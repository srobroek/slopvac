mod pcre;
use pcre::{Limits, MatchCtx, Regex};
use serde::Deserialize;
use serde_json::{json, Value};
use std::time::Instant;

#[derive(Deserialize)]
struct Pat {
    rule_id: String,
    pattern: String,
    ignore_case: bool,
}
#[derive(Deserialize)]
struct Corpus {
    texts: Vec<String>,
}

/// Limits policy under test. Override with
/// LIMITS="match,depth,heap_kib,jit_stack_bytes,jit_match" (0 = unset).
fn policy() -> Limits {
    let v: Vec<u64> = std::env::var("LIMITS")
        .unwrap_or("10000000,10000000,262144,8388608,100000".into())
        .split(',')
        .map(|s| s.parse().unwrap())
        .collect();
    let o = |x: u64| if x == 0 { None } else { Some(x) };
    Limits {
        match_limit: o(v[0]).map(|x| x as u32),
        depth_limit: o(v[1]).map(|x| x as u32),
        heap_limit_kib: o(v[2]).map(|x| x as u32),
        jit_stack: o(v[3]).map(|x| x as usize),
        jit_match_limit: v.get(4).copied().and_then(o).map(|x| x as u32),
    }
}

fn target() -> String {
    let env = if cfg!(target_env = "musl") {
        "musl"
    } else if cfg!(target_env = "gnu") {
        "gnu"
    } else if cfg!(target_env = "msvc") {
        "msvc"
    } else {
        ""
    };
    format!(
        "{}-{}-{}",
        std::env::consts::ARCH,
        std::env::consts::OS,
        env
    )
}

fn info() -> Value {
    use pcre2_sys::*;
    json!({
        "target": target(),
        "pcre2_version": pcre::config_str(PCRE2_CONFIG_VERSION),
        "unicode_version": pcre::config_str(PCRE2_CONFIG_UNICODE_VERSION),
        "jit_configured": pcre::config_u32(PCRE2_CONFIG_JIT) == 1,
        "default_match_limit": pcre::config_u32(PCRE2_CONFIG_MATCHLIMIT),
        "default_depth_limit": pcre::config_u32(PCRE2_CONFIG_DEPTHLIMIT),
        "default_heap_limit_kib": pcre::config_u32(PCRE2_CONFIG_HEAPLIMIT),
        "pcre2_crate_version": format!("{:?}", pcre2::version()),
        "pcre2_crate_jit": pcre2::is_jit_available(),
    })
}

fn cp_index(t: &str) -> Vec<u32> {
    let mut idx = vec![0u32; t.len() + 1];
    let mut c = 0u32;
    for (b, ch) in t.char_indices() {
        for k in 0..ch.len_utf8() {
            idx[b + k] = c;
        }
        c += 1;
    }
    idx[t.len()] = c;
    idx
}

enum Eng {
    Own(Regex, bool),
    Crate(pcre2::bytes::Regex),
}

fn build(mode: &str, p: &Pat) -> Result<Eng, String> {
    match mode {
        "jit" => Regex::new(&p.pattern, p.ignore_case, true).map(|r| Eng::Own(r, true)),
        "interp" => Regex::new(&p.pattern, p.ignore_case, false).map(|r| Eng::Own(r, false)),
        "crate" => pcre2::bytes::RegexBuilder::new()
            .utf(true)
            .ucp(true)
            .caseless(p.ignore_case)
            .jit_if_available(true)
            .build(&p.pattern)
            .map(Eng::Crate)
            .map_err(|e| e.to_string()),
        _ => unreachable!(),
    }
}

fn run(e: &Eng, ctx: &MatchCtx, t: &str) -> Result<Vec<(usize, usize)>, String> {
    match e {
        Eng::Own(r, jit) => pcre::find_all(r, ctx, t, *jit).map_err(pcre::error_message),
        Eng::Crate(r) => r
            .find_iter(t.as_bytes())
            .map(|m| m.map(|m| (m.start(), m.end())).map_err(|e| e.to_string()))
            .collect(),
    }
}

fn dump(patfile: &str, corpusfile: &str, out: &str, mode: &str) {
    let pats: Vec<Pat> = serde_json::from_slice(&std::fs::read(patfile).unwrap()).unwrap();
    let corpus: Corpus = serde_json::from_slice(&std::fs::read(corpusfile).unwrap()).unwrap();
    let idx: Vec<Vec<u32>> = corpus.texts.iter().map(|t| cp_index(t)).collect();
    let lim = policy();
    let ctx = MatchCtx::new(lim);
    let t0 = Instant::now();
    let engs: Vec<Result<Eng, String>> = pats.iter().map(|p| build(mode, p)).collect();
    let compile_ms = t0.elapsed().as_secs_f64() * 1e3;
    let jit_patterns = engs
        .iter()
        .filter(|e| matches!(e, Ok(Eng::Own(r, _)) if r.jit))
        .count();
    let mut compile_errors = vec![];
    let mut runtime_errors = vec![];
    let mut matches = serde_json::Map::new();
    let mut per_ms = serde_json::Map::new();
    let mut nmatch = 0usize;
    let t1 = Instant::now();
    for (pi, (p, e)) in pats.iter().zip(&engs).enumerate() {
        let e = match e {
            Ok(e) => e,
            Err(m) => {
                compile_errors.push(json!([p.rule_id, m]));
                continue;
            }
        };
        let tp = Instant::now();
        let mut per = vec![];
        for (ti, t) in corpus.texts.iter().enumerate() {
            match run(e, &ctx, t) {
                Ok(v) if !v.is_empty() => {
                    nmatch += v.len();
                    let ix = &idx[ti];
                    let spans: Vec<_> = v.iter().map(|&(s, e)| [ix[s], ix[e]]).collect();
                    per.push(json!([ti, spans]));
                }
                Ok(_) => {}
                Err(m) => runtime_errors.push(json!([pi, ti, m])),
            }
        }
        per_ms.insert(pi.to_string(), json!(tp.elapsed().as_secs_f64() * 1e3));
        matches.insert(pi.to_string(), Value::Array(per));
    }
    let run_ms = t1.elapsed().as_secs_f64() * 1e3;
    eprintln!(
        "{mode} {corpusfile}: compiled {}/{} ({jit_patterns} JIT) {compile_ms:.1}ms run {run_ms:.1}ms matches {nmatch} runtime errors {}",
        pats.len() - compile_errors.len(),
        pats.len(),
        runtime_errors.len()
    );
    let res = json!({"info": info(), "mode": mode, "limits": format!("{lim:?}"), "jit_patterns": jit_patterns,
        "compile_errors": compile_errors, "runtime_errors": runtime_errors, "matches": matches,
        "compile_ms": compile_ms, "run_ms": run_ms, "per_pattern_ms": per_ms, "n_matches": nmatch,
        "jit_stack_fallbacks": pcre::JIT_FALLBACKS.load(std::sync::atomic::Ordering::Relaxed)});
    std::fs::write(out, res.to_string()).unwrap();
}

/// Unicode class membership over every scalar value, and caseless equivalence sets.
fn classes(caseprobe: &str, out: &str) {
    let all: String = (0u32..=0x10FFFF).filter_map(char::from_u32).collect();
    let ix = cp_index(&all);
    let to_cp = |b: usize| all[b..].chars().next().unwrap() as u32;
    let ctx = MatchCtx::new(policy());
    let mut res = serde_json::Map::new();
    for cls in [
        r"\w",
        r"\s",
        r"\d",
        r"\b",
        r"[[:alpha:]]",
        r"(?i)[a-z]",
        r"(?m)$",
        r"$",
    ] {
        let re = Regex::new(cls, false, true).unwrap();
        let v = pcre::find_all(&re, &ctx, &all, re.jit).unwrap();
        let cps: Vec<u32> = if cls.contains('$') || cls == r"\b" {
            v.iter().map(|&(s, _)| ix[s]).collect()
        } else {
            v.iter().map(|&(s, _)| to_cp(s)).collect()
        };
        res.insert(cls.to_string(), json!(cps));
    }
    let probe: Vec<u32> = serde_json::from_slice(&std::fs::read(caseprobe).unwrap()).unwrap();
    let hay: String = probe.iter().filter_map(|&c| char::from_u32(c)).collect();
    let mut fold = serde_json::Map::new();
    for &c in &probe {
        let re = Regex::new(&format!(r"\x{{{c:x}}}"), true, true).unwrap();
        let v = pcre::find_all(&re, &ctx, &hay, re.jit).unwrap();
        let mut set: Vec<u32> = v
            .iter()
            .map(|&(s, _)| hay[s..].chars().next().unwrap() as u32)
            .collect();
        set.sort();
        fold.insert(c.to_string(), json!(set));
    }
    res.insert("caseless".into(), Value::Object(fold));
    std::fs::write(out, Value::Object(res).to_string()).unwrap();
}

/// Show each limit firing on a catastrophic pattern, in both engines.
fn limits_demo(out: &str) {
    let cases: Vec<(&str, &str, String)> = vec![
        (
            "nested-quantifier",
            r"^(\w+\s?)*$",
            format!("{}!", "a".repeat(40)),
        ),
        (
            "nested-quantifier-big",
            r"^(\w+\s?)*$",
            format!("{}!", "word ".repeat(200_000)),
        ),
        (
            "deep-group",
            r"^(a|b)*$",
            format!("{}c", "ab".repeat(500_000)),
        ),
        // Real slopvac rule (rhetorical-question-transition) on a 1 MB run of spaces: JIT only
        // checks for the required '?' within 500 KB (REQ_CU_MAX*100), then backtracks quadratically.
        (
            "rhetorical-question-1MB-spaces",
            r"(?im)^\s*(?:#{1,6}\s*)?(?:So|But|Now|And)?\s*(?:why|what|how|who)\b[^.!?\n]{0,60}\?\s*$",
            " ".repeat(1_000_000),
        ),
        (
            "lookbehind-scan",
            r"(?<=\b(?:which|where)(?:\s{1,3}[\w-]{1,40}){0,2}\s{1,3})will",
            "which ".repeat(1_000_000),
        ),
    ];
    let none = Limits {
        match_limit: None,
        depth_limit: None,
        heap_limit_kib: None,
        jit_match_limit: None,
        jit_stack: None,
    };
    let big = Some(8usize << 20);
    let configs: Vec<(&str, Limits)> = vec![
        ("pcre2-defaults", none),
        ("policy", policy()),
        (
            "match=100k",
            Limits {
                match_limit: Some(100_000),
                jit_match_limit: Some(100_000),
                jit_stack: big,
                ..none
            },
        ),
        (
            "depth=10k",
            Limits {
                depth_limit: Some(10_000),
                jit_stack: big,
                ..none
            },
        ),
        (
            "heap=1MiB",
            Limits {
                heap_limit_kib: Some(1024),
                jit_stack: big,
                ..none
            },
        ),
        (
            "jitstack=64KiB",
            Limits {
                jit_stack: Some(64 << 10),
                ..none
            },
        ),
    ];
    let mut rows = vec![];
    for (name, pat, text) in &cases {
        for jit in [true, false] {
            let re = Regex::new(pat, false, jit).unwrap();
            for (cname, l) in &configs {
                if jit && re.jit && name.starts_with("rhetorical") && l.jit_match_limit.is_none() {
                    // JIT at the default 10M budget takes ~10 min here (measured 597 s on M-series).
                    continue;
                }
                let ctx = MatchCtx::new(*l);
                let t = Instant::now();
                let fb0 = pcre::JIT_FALLBACKS.load(std::sync::atomic::Ordering::Relaxed);
                let r = pcre::find_all(&re, &ctx, text, jit && re.jit);
                let fb = pcre::JIT_FALLBACKS.load(std::sync::atomic::Ordering::Relaxed) - fb0;
                let ms = t.elapsed().as_secs_f64() * 1e3;
                let mut outcome = match r {
                    Ok(v) => format!("ok {} matches", v.len()),
                    Err(e) => pcre::error_message(e),
                };
                if fb > 0 {
                    outcome = format!("JIT limit/stack hit -> interpreter: {outcome}");
                }
                eprintln!(
                    "{name:22} {:6} {cname:15} {ms:9.1}ms  {outcome}",
                    if jit && re.jit { "jit" } else { "interp" }
                );
                rows.push(json!({"case": name, "input_bytes": text.len(), "engine": if jit && re.jit {"jit"} else {"interp"},
                    "limits": cname, "ms": ms, "outcome": outcome}));
            }
        }
    }
    std::fs::write(out, json!({"info": info(), "rows": rows}).to_string()).unwrap();
}

fn main() {
    let a: Vec<String> = std::env::args().collect();
    match a[1].as_str() {
        "info" => println!("{}", serde_json::to_string_pretty(&info()).unwrap()),
        "dump" => dump(&a[2], &a[3], &a[4], &a[5]),
        "classes" => classes(&a[2], &a[3]),
        "limits" => limits_demo(&a[2]),
        _ => panic!("usage: info | dump PAT CORPUS OUT jit|interp|crate | classes CASEPROBE OUT | limits OUT"),
    }
}
