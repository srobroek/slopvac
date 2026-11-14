//! Thin safe wrapper over pcre2-sys: compile (UTF+UCP), optional JIT, a match
//! context with match/depth/heap limits and a JIT stack, and a Python-compatible
//! non-overlapping iterator (empty match after an empty match is retried with
//! PCRE2_NOTEMPTY_ATSTART, as CPython `re` / `regex` do).
use pcre2_sys::*;
use std::ptr;

pub fn error_message(code: i32) -> String {
    let mut buf = vec![0u8; 256];
    let n = unsafe { pcre2_get_error_message_8(code, buf.as_mut_ptr(), buf.len()) };
    if n < 0 {
        return format!("pcre2 error {code}");
    }
    buf.truncate(n as usize);
    format!("{} ({code})", String::from_utf8_lossy(&buf))
}

pub fn config_u32(what: u32) -> u32 {
    let mut v: u32 = 0;
    unsafe { pcre2_config_8(what, &mut v as *mut u32 as *mut libc::c_void) };
    v
}

pub fn config_str(what: u32) -> String {
    let mut buf = vec![0u8; 64];
    let n = unsafe { pcre2_config_8(what, buf.as_mut_ptr() as *mut libc::c_void) };
    buf.truncate((n.max(1) - 1) as usize);
    String::from_utf8_lossy(&buf).into_owned()
}

pub struct Regex {
    code: *mut pcre2_code_8,
    pub jit: bool,
}
unsafe impl Send for Regex {}
unsafe impl Sync for Regex {}

impl Drop for Regex {
    fn drop(&mut self) {
        unsafe { pcre2_code_free_8(self.code) }
    }
}

impl Regex {
    pub fn new(pattern: &str, caseless: bool, want_jit: bool) -> Result<Regex, String> {
        let mut opts = PCRE2_UTF | PCRE2_UCP;
        if caseless {
            opts |= PCRE2_CASELESS;
        }
        let (mut ec, mut eo) = (0i32, 0usize);
        let code = unsafe {
            pcre2_compile_8(
                pattern.as_ptr(),
                pattern.len(),
                opts,
                &mut ec,
                &mut eo,
                ptr::null_mut(),
            )
        };
        if code.is_null() {
            return Err(format!("{} at offset {eo}", error_message(ec)));
        }
        let mut re = Regex { code, jit: false };
        if want_jit {
            let rc = unsafe { pcre2_jit_compile_8(code, PCRE2_JIT_COMPLETE) };
            // On builds without SUPPORT_JIT this returns PCRE2_ERROR_JIT_BADOPTION
            // and pcre2_match falls back to the interpreter.
            re.jit = rc == 0;
        }
        Ok(re)
    }
}

#[derive(Clone, Copy, Debug)]
pub struct Limits {
    /// Interpreter match() call budget per pcre2_match call.
    pub match_limit: Option<u32>,
    /// Interpreter backtracking depth.
    pub depth_limit: Option<u32>,
    /// KiB, interpreter only.
    pub heap_limit_kib: Option<u32>,
    /// JIT budget (JIT counts differently and its cost per unit is not bounded,
    /// see RESULTS); on hitting it the call is redone on the interpreter.
    pub jit_match_limit: Option<u32>,
    /// bytes; JIT only. None = PCRE2's 32 KiB machine-stack default.
    pub jit_stack: Option<usize>,
}

/// Two match contexts: JIT (jit_match_limit + JIT stack) and interpreter
/// (match/depth/heap limits). The interpreter context is also the fallback.
pub struct MatchCtx {
    jit: *mut pcre2_match_context_8,
    interp: *mut pcre2_match_context_8,
    stack: *mut pcre2_jit_stack_8,
}
impl Drop for MatchCtx {
    fn drop(&mut self) {
        unsafe {
            if !self.stack.is_null() {
                pcre2_jit_stack_free_8(self.stack);
            }
            pcre2_match_context_free_8(self.jit);
            pcre2_match_context_free_8(self.interp);
        }
    }
}
impl MatchCtx {
    pub fn new(l: Limits) -> MatchCtx {
        unsafe {
            let interp = pcre2_match_context_create_8(ptr::null_mut());
            let jit = pcre2_match_context_create_8(ptr::null_mut());
            assert!(!interp.is_null() && !jit.is_null());
            if let Some(v) = l.match_limit {
                pcre2_set_match_limit_8(interp, v);
            }
            if let Some(v) = l.depth_limit {
                pcre2_set_depth_limit_8(interp, v);
            }
            if let Some(v) = l.heap_limit_kib {
                pcre2_set_heap_limit_8(interp, v);
            }
            if let Some(v) = l.jit_match_limit {
                pcre2_set_match_limit_8(jit, v);
            }
            let mut stack = ptr::null_mut();
            // pcre2_jit_stack_create returns NULL on builds without JIT support.
            if let (Some(max), true) = (l.jit_stack, config_u32(PCRE2_CONFIG_JIT) == 1) {
                stack = pcre2_jit_stack_create_8(32 * 1024, max, ptr::null_mut());
                assert!(!stack.is_null());
                pcre2_jit_stack_assign_8(jit, None, stack as *mut libc::c_void);
            }
            MatchCtx { jit, interp, stack }
        }
    }
}

pub struct MatchData(*mut pcre2_match_data_8);
impl Drop for MatchData {
    fn drop(&mut self) {
        unsafe { pcre2_match_data_free_8(self.0) }
    }
}

static EMPTY: &[u8] = &[0];
pub static JIT_FALLBACKS: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);

/// All non-overlapping matches as byte spans, CPython semantics.
pub fn find_all(
    re: &Regex,
    ctx: &MatchCtx,
    text: &str,
    use_jit: bool,
) -> Result<Vec<(usize, usize)>, i32> {
    let md = MatchData(unsafe { pcre2_match_data_create_from_pattern_8(re.code, ptr::null_mut()) });
    assert!(!md.0.is_null());
    let subj = if text.is_empty() {
        EMPTY.as_ptr()
    } else {
        text.as_ptr()
    };
    let len = text.len();
    let mut out = vec![];
    let mut pos = 0usize;
    let mut notempty = false;
    // &str is valid UTF-8 and every start offset is a char boundary, so skip
    // PCRE2's per-call UTF check (it is O(n) per call: quadratic on big inputs).
    let base = PCRE2_NO_UTF_CHECK | if use_jit { 0 } else { PCRE2_NO_JIT };
    loop {
        if pos > len {
            break;
        }
        let opts = base | if notempty { PCRE2_NOTEMPTY_ATSTART } else { 0 };
        let mctx = if use_jit { ctx.jit } else { ctx.interp };
        let mut rc = unsafe { pcre2_match_8(re.code, subj, len, pos, opts, md.0, mctx) };
        if use_jit && (rc == PCRE2_ERROR_JIT_STACKLIMIT || rc == PCRE2_ERROR_MATCHLIMIT) {
            // JIT budget or stack exhausted: redo this call on the interpreter,
            // bounded by its match/depth/heap limits. Results then equal the
            // non-JIT targets (aarch64-musl); only interpreter limits can fail.
            JIT_FALLBACKS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
            rc = unsafe {
                pcre2_match_8(
                    re.code,
                    subj,
                    len,
                    pos,
                    opts | PCRE2_NO_JIT,
                    md.0,
                    ctx.interp,
                )
            };
        }
        if rc == PCRE2_ERROR_NOMATCH {
            break;
        }
        if rc < 0 {
            return Err(rc);
        }
        let ov = unsafe { std::slice::from_raw_parts(pcre2_get_ovector_pointer_8(md.0), 2) };
        let (s, e) = (ov[0], ov[1]);
        out.push((s, e));
        // \K or lookahead tricks can yield e < s; not used by slopvac, guard anyway.
        pos = e.max(s);
        notempty = s == e;
    }
    Ok(out)
}
