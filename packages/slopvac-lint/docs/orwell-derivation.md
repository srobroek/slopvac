# Orwell's Six Rules as an Objective Ruleset

Source texts read in full:

- George Orwell, "Politics and the English Language", *Horizon*, April 1946 — <https://www.orwell.ru/library/essays/politics/english/e_polit/>
- Duke Graduate School Scientific Writing Resource, "Orwell's 6 Rules" — <https://sites.duke.edu/scientificwriting/orwells-6-rules/> (rule text only; the page carries no gloss)

Scope: a Vale regex ruleset plus an agentic reviewer that judges AI-generated
prose. Blocks marked **EXTENSION** go beyond Orwell; each names its warrant in
the essay.

---

## The six rules, verbatim

Orwell's exact 1946 wording, in his order:

1. "Never use a metaphor, simile, or other figure of speech which you are used to seeing in print."
2. "Never use a long word where a short one will do."
3. "If it is possible to cut a word out, always cut it out."
4. "Never use the passive where you can use the active."
5. "Never use a foreign phrase, a scientific word, or a jargon word if you can think of an everyday English equivalent."
6. "Break any of these rules sooner than say anything outright barbarous."

Orwell gives no per-rule commentary. His gloss is the paragraph that introduces
them and the paragraph that follows them.

Introducing the rules:

> "But one can often be in doubt about the effect of a word or a phrase, and one needs rules that one can rely on when instinct fails. I think the following rules will cover most cases"

The rules are therefore a fallback for the case where judgement is absent — the
exact case a linter and an automated reviewer occupy.

Immediately before that, the standard the rules serve:

> "What is above all needed is to let the meaning choose the word, and not the other way around. In prose, the worst thing one can do with words is surrender to them."

And:

> "Nor does it even imply in every case preferring the Saxon word to the Latin one, though it does imply using the fewest and shortest words that will cover one's meaning."

That sentence is the operative limit on rules 2, 3 and 5: **fewest and shortest
words that cover the meaning**, not fewest and shortest words.

Following the rules:

> "These rules sound elementary, and so they are, but they demand a deep change of attitude in anyone who has grown used to writing in the style now fashionable. One could keep all of them and still write bad English, but one could not write the kind of stuff that I quoted in those five specimens at the beginning of this article."

Orwell states the ceiling himself: full compliance is necessary, not sufficient.
A conformant document can still be bad. That licenses the agentic reviewer to
carry judgements the regex layer cannot.

Two explicit exclusions Orwell attaches to the whole programme:

> "It has nothing to do with correct grammar and syntax, which are of no importance so long as one makes one's meaning clear, or with the avoidance of Americanisms, or with having what is called a 'good prose style'. On the other hand, it is not concerned with fake simplicity and the attempt to make written English colloquial."

So: no grammar pedantry, no dialect policing, and no reward for dumbing down.

---

## Orwell's supporting argument

### The taxonomy, verbatim

Orwell's four-part catalogue is more mechanizable than the six rules, because
each category ships with a token list. Quoted in full.

**DYING METAPHORS.**

> "A newly invented metaphor assists thought by evoking a visual image, while on the other hand a metaphor which is technically 'dead' (e. g. iron resolution) has in effect reverted to being an ordinary word and can generally be used without loss of vividness. But in between these two classes there is a huge dump of worn-out metaphors which have lost all evocative power and are merely used because they save people the trouble of inventing phrases for themselves. Examples are: Ring the changes on, take up the cudgel for, toe the line, ride roughshod over, stand shoulder to shoulder with, play into the hands of, no axe to grind, grist to the mill, fishing in troubled waters, on the order of the day, Achilles' heel, swan song, hotbed. Many of these are used without knowledge of their meaning (what is a 'rift', for instance?), and incompatible metaphors are frequently mixed, a sure sign that the writer is not interested in what he is saying. Some metaphors now current have been twisted out of their original meaning without those who use them even being aware of the fact. For example, toe the line is sometimes written as tow the line. Another example is the hammer and the anvil, now always used with the implication that the anvil gets the worst of it. In real life it is always the anvil that breaks the hammer, never the other way about: a writer who stopped to think what he was saying would avoid perverting the original phrase."

Three testable facts sit in that paragraph: a fully dead metaphor is *allowed*
("can generally be used without loss of vividness"); a fresh metaphor is
*wanted*; only the middle band is a violation. Any linter that flags "iron
resolution" has misread the rule.

**OPERATORS OR VERBAL FALSE LIMBS.**

> "These save the trouble of picking out appropriate verbs and nouns, and at the same time pad each sentence with extra syllables which give it an appearance of symmetry. Characteristic phrases are render inoperative, militate against, make contact with, be subjected to, give rise to, give grounds for, have the effect of, play a leading part (role) in, make itself felt, take effect, exhibit a tendency to, serve the purpose of, etc., etc. The keynote is the elimination of simple verbs. Instead of being a single word, such as break, stop, spoil, mend, kill, a verb becomes a phrase, made up of a noun or adjective tacked on to some general-purpose verb such as prove, serve, form, play, render. In addition, the passive voice is wherever possible used in preference to the active, and noun constructions are used instead of gerunds (by examination of instead of by examining). The range of verbs is further cut down by means of the -ize and de- formations, and the banal statements are given an appearance of profundity by means of the not un- formation. Simple conjunctions and prepositions are replaced by such phrases as with respect to, having regard to, the fact that, by dint of, in view of, in the interests of, on the hypothesis that; and the ends of sentences are saved by anticlimax by such resounding commonplaces as greatly to be desired, cannot be left out of account, a development to be expected in the near future, deserving of serious consideration, brought to a satisfactory conclusion, and so on and so forth."

This is the single richest paragraph for mechanization. It names five distinct
patterns, each regexable: light-verb-plus-nominalization, passive preference,
noun-for-gerund, `-ize`/`de-` coinage, and `not un-`.

**PRETENTIOUS DICTION.**

> "Words like phenomenon, element, individual (as noun), objective, categorical, effective, virtual, basic, primary, promote, constitute, exhibit, exploit, utilize, eliminate, liquidate, are used to dress up a simple statement and give an air of scientific impartiality to biased judgements. Adjectives like epoch-making, epic, historic, unforgettable, triumphant, age-old, inevitable, inexorable, veritable, are used to dignify the sordid process of international politics, while writing that aims at glorifying war usually takes on an archaic colour, its characteristic words being: realm, throne, chariot, mailed fist, trident, sword, shield, buckler, banner, jackboot, clarion. Foreign words and expressions such as cul de sac, ancien regime, deus ex machina, mutatis mutandis, status quo, gleichschaltung, weltanschauung, are used to give an air of culture and elegance. Except for the useful abbreviations i. e., e. g. and etc., there is no real need for any of the hundreds of foreign phrases now current in the English language. Bad writers, and especially scientific, political, and sociological writers, are nearly always haunted by the notion that Latin or Greek words are grander than Saxon ones, and unnecessary words like expedite, ameliorate, predict, extraneous, deracinated, clandestine, subaqueous, and hundreds of others constantly gain ground from their Anglo-Saxon numbers. The jargon peculiar to Marxist writing (hyena, hangman, cannibal, petty bourgeois, these gentry, lackey, flunkey, mad dog, White Guard, etc.) consists largely of words translated from Russian, German, or French; but the normal way of coining a new word is to use Latin or Greek root with the appropriate affix and, where necessary, the size formation. It is often easier to make up words of this kind (deregionalize, impermissible, extramarital, non-fragmentary and so forth) than to think up the English words that will cover one's meaning. The result, in general, is an increase in slovenliness and vagueness."

Note the stated *function*: pretentious diction "give[s] an air of scientific
impartiality to biased judgements". The complaint is not aesthetic. It is that
register is used as a substitute for evidence. That is the hinge on which the
"scientific words" clause re-aims at modern jargon.

**MEANINGLESS WORDS.**

> "In certain kinds of writing, particularly in art criticism and literary criticism, it is normal to come across long passages which are almost completely lacking in meaning. Words like romantic, plastic, values, human, dead, sentimental, natural, vitality, as used in art criticism, are strictly meaningless, in the sense that they not only do not point to any discoverable object, but are hardly ever expected to do so by the reader. When one critic writes, 'The outstanding feature of Mr. X's work is its living quality', while another writes, 'The immediately striking thing about Mr. X's work is its peculiar deadness', the reader accepts this as a simple difference opinion. If words like black and white were involved, instead of the jargon words dead and living, he would see at once that language was being used in an improper way. Many political words are similarly abused. The word Fascism has now no meaning except in so far as it signifies 'something not desirable'. The words democracy, socialism, freedom, patriotic, realistic, justice have each of them several different meanings which cannot be reconciled with one another. In the case of a word like democracy, not only is there no agreed definition, but the attempt to make one is resisted from all sides. It is almost universally felt that when we call a country democratic we are praising it: consequently the defenders of every kind of regime claim that it is a democracy, and fear that they might have to stop using that word if it were tied down to any one meaning. Words of this kind are often used in a consciously dishonest way. That is, the person who uses them has his own private definition, but allows his hearer to think he means something quite different. Statements like Marshal Petain was a true patriot, The Soviet press is the freest in the world, The Catholic Church is opposed to persecution, are almost always made with intent to deceive. Other words used in variable meanings, in most cases more or less dishonestly, are: class, totalitarian, science, progressive, reactionary, bourgeois, equality."

The test buried here is the best objective test in the essay: **does the word
point to a discoverable object, and would its negation be recognized as a
disagreement about fact rather than a difference of opinion?** "Living quality"
versus "peculiar deadness" fails. "Black" versus "white" passes.

### The catalogue of examples

Orwell's five specimens and his own diagnosis of each — the diagnosis is the
part a reviewer can reuse as a rubric.

| # | Source | Orwell's diagnosis (quoted) |
| --- | --- | --- |
| 1 | Prof. Harold Laski, *Freedom of Expression* | "uses five negatives in fifty three words. One of these is superfluous, making nonsense of the whole passage, and in addition there is the slip — alien for akin" |
| 2 | Prof. Lancelot Hogben, *Interglossia* | "plays ducks and drakes with a battery which is able to write prescriptions, and, while disapproving of the everyday phrase put up with, is unwilling to look egregious up in the dictionary and see what it means" |
| 3 | Essay on psychology in *Politics* (New York) | "if one takes an uncharitable attitude towards it, is simply meaningless: probably one could work out its intended meaning by reading the whole of the article in which it occurs" |
| 4 | Communist pamphlet | "the writer knows more or less what he wants to say, but an accumulation of stale phrases chokes him like tea leaves blocking a sink" |
| 5 | Letter in *Tribune* | "words and meaning have almost parted company" |

Two faults are common to all five:

> "The first is staleness of imagery; the other is lack of precision."

Orwell's summary of the writer's state in every case:

> "The writer either has a meaning and cannot express it, or he inadvertently says something else, or he is almost indifferent as to whether his words mean anything or not."

That trichotomy is a usable severity scale: *cannot express* (fixable by
rewrite), *says something else* (factual defect), *indifferent* (the text has no
propositional content to repair).

His four-plus-two revision questions, verbatim, are the reviewer's checklist:

> "What am I trying to say? What words will express it? What image or idiom will make it clearer? Is this image fresh enough to have an effect? ... Could I put it more shortly? Have I said anything that is avoidably ugly?"

### The "concrete becomes abstract" mechanism

Stated first as a general tendency:

> "As soon as certain topics are raised, the concrete melts into the abstract and no one seems able to think of turns of speech that are not hackneyed: prose consists less and less of words chosen for the sake of their meaning, and more and more of phrases tacked together like the sections of a prefabricated hen-house."

Then demonstrated. Ecclesiastes 9:11:

> "I returned and saw under the sun, that the race is not to the swift, nor the battle to the strong, neither yet bread to the wise, nor yet riches to men of understanding, nor yet favour to men of skill; but time and chance happeneth to them all."

Orwell's translation into "modern English of the worst sort":

> "Objective considerations of contemporary phenomena compel the conclusion that success or failure in competitive activities exhibits no tendency to be commensurate with innate capacity, but that a considerable element of the unpredictable must invariably be taken into account."

His measurement of the two — quantities, not impressions:

> "The first contains forty-nine words but only sixty syllables, and all its words are those of everyday life. The second contains thirty-eight words of ninety syllables: eighteen of those words are from Latin roots, and one from Greek. The first sentence contains six vivid images, and only one phrase ('time and chance') that could be called vague. The second contains not a single fresh, arresting phrase, and in spite of its ninety syllables it gives only a shortened version of the meaning contained in the first."

The mechanism named exactly:

> "in the middle the concrete illustrations — race, battle, bread — dissolve into the vague phrases 'success or failure in competitive activities'. This had to be so, because no modern writer of the kind I am discussing — no one capable of using phrases like 'objective considerations of contemporary phenomena' — would ever tabulate his thoughts in that precise and detailed way."

Four countable metrics fall straight out: syllables per word, count of
Latin/Greek-rooted words, count of concrete referents, count of vague phrases.
Orwell's own comparison is 60/49 = 1.22 syllables per word against 90/38 = 2.37.

The production process he is describing:

> "modern writing at its worst does not consist in picking out words for the sake of their meaning and inventing images in order to make the meaning clearer. It consists in gumming together long strips of words which have already been set in order by someone else, and making the results presentable by sheer humbug. The attraction of this way of writing is that it is easy."

And the image-clash diagnostic:

> "The sole aim of a metaphor is to call up a visual image. When these images clash — as in The Fascist octopus has sung its swan song, the jackboot is thrown into the melting pot — it can be taken as certain that the writer is not seeing a mental image of the objects he is naming; in other words he is not really thinking."

Why euphemism specifically:

> "Defenceless villages are bombarded from the air, the inhabitants driven out into the countryside, the cattle machine-gunned, the huts set on fire with incendiary bullets: this is called pacification. Millions of peasants are robbed of their farms and sent trudging along the roads with no more than they can carry: this is called transfer of population or rectification of frontiers. People are imprisoned for years without trial, or shot in the back of the neck or sent to die of scurvy in Arctic lumber camps: this is called elimination of unreliable elements. Such phraseology is needed if one wants to name things without calling up mental pictures of them."

> "The inflated style itself is a kind of euphemism. A mass of Latin words falls upon the facts like soft snow, blurring the outline and covering up all the details. The great enemy of clear language is insincerity."

Finally, the passage that authorizes a *token blocklist* as a method rather than
a crutch:

> "Silly words and expressions have often disappeared, not through any evolutionary process but owing to the conscious action of a minority. Two recent examples were explore every avenue and leave no stone unturned, which were killed by the jeers of a few journalists. There is a long list of flyblown metaphors which could similarly be got rid of if enough people would interest themselves in the job"

Orwell's method is a curated list, enforced socially. A Vale rule is that list,
enforced mechanically.

---

## The modernized ruleset

Conventions used in every block:

- Violations are reported against a **span**, not a sentence.
- An exception must be *named* in an inline annotation to suppress a finding:
  `<!-- orwell-allow: rule=<id> reason=<exception-name> -->`. Silent suppression
  is itself a violation (see `named-exception-only`).
- "Countable" means the reviewer reports an integer, and the threshold is
  configuration, not opinion.

---

### 1. `stale-figure`

**Orwell's original:** "Never use a metaphor, simile, or other figure of speech which you are used to seeing in print."

**Restated rule:** Use no figure of speech that appears on the stale-figure token
list or that returns more than a threshold number of verbatim web matches; write
a fresh image or drop the image entirely.

**Objective test:** Is the figure on the token list? If it is a candidate not yet
listed, quote it exactly and count corpus hits. Orwell's own criterion —
"which you are used to seeing in print" — is frequency, so frequency is the
measurement. A figure is stale when it is neither fully lexicalized (a dead
metaphor that "has in effect reverted to being an ordinary word") nor original.
Decision procedure, in order:

1. Does the phrase appear in the `dying_metaphors` or `llm_cliches` token list? → violation.
2. Is it a single lexicalized word or a fixed compound with a dictionary sense ("deadline", "bottleneck", "iron resolution")? → allowed.
3. Otherwise, count verbatim occurrences in the reference corpus. Above the configured threshold → violation.

**Mechanizable?** YES for the listed band, PARTIAL overall (step 3 needs a
corpus). Vale `existence` with `tokens:` from the lists below. Starter regex for
the AI-era layer:

```
\b(?:tip of the iceberg|double[- ]edged sword|low[- ]hanging fruit|move the needle|moving the needle|game[- ]chang(?:er|ing)|paradigm shift|perfect storm|silver bullet|holy grail|north star|secret sauce|force multiplier|sea change|deep dive|boil(?:s|ing)? the ocean|at the end of the day|when it comes to|in today's (?:fast[- ]paced |ever[- ]evolving |rapidly changing )?(?:world|landscape)|navigat(?:e|ing) the (?:complex(?:ities of )?|ever[- ]changing )?\w+|in the (?:realm|world|landscape|tapestry) of|a testament to|stands? as a testament|unlock(?:s|ing)? the (?:power|potential)|harness(?:es|ing)? the power)\b
```

**AI failure mode:** LLM prose is trained on the stale band and reproduces it as
default register. Three characteristic forms:

- **Opening scaffolds.** "In today's rapidly evolving landscape of distributed systems…" — the figure ("landscape") carries no image and no information.
- **Closing elevation.** "This stands as a testament to the power of thoughtful design." A figure used to signal that the section has ended.
- **Compulsory metaphor per abstraction.** Every noun gets an image whether or not one clarifies: "the beating heart of the pipeline", "the connective tissue between services", "the north star metric". Orwell's diagnosis applies directly — "he is not seeing a mental image of the objects he is naming".

**Named exceptions:**

1. **Dead metaphor.** Single word or fixed compound with an established literal dictionary sense (bottleneck, deadline, pipeline, branch, root, tree, stack, thread, handshake, orphan).
2. **Domain term.** The figure *is* the technical name of the thing and has no non-figurative synonym in the domain's own vocabulary.
3. **Quotation.** Inside quotation marks with an attributed source, or inside a fenced code block, log excerpt, or transcript.
4. **Named-entity.** Product, project, error-code, or standard name.
5. **Fresh figure.** Original to this document and below the corpus threshold; the writer may be asked to defend it once, not repeatedly.

**Fix move:** Delete the figure and state the underlying fact. If the figure was
carrying real information, replace it with the measurement or the concrete
referent it stood in for.

---

### 2. `short-word-first`

**Orwell's original:** "Never use a long word where a short one will do."

**Restated rule:** Where a mapped shorter substitute preserves the exact
denotation, use the shorter word; length is licensed only by precision, never by
register.

**Objective test:** For each word of four or more syllables (or on the Latinate
list), is there an entry in the substitution table? If yes, substitute it and ask
the single question: **does the sentence now assert anything different?** If the
assertion is unchanged, the long word is a violation. The count reported is
`n_substitutable_long_words`. Orwell's own guard is the ceiling: "using the
fewest and shortest words that will cover one's meaning" — and explicitly *not*
Saxon-for-Latin as a reflex ("Nor does it even imply in every case preferring the
Saxon word to the Latin one").

Secondary countable metric, taken from Orwell's own arithmetic on the
Ecclesiastes pair: **syllables per word**. His good sentence scores 1.22, his bad
one 2.37. Report the document's mean and flag paragraphs above the configured
ceiling.

**Mechanizable?** YES. Vale `substitution` extension point with a bounded
map — the substitution is proposed mechanically, the denotation check is the
reviewer's. Starter map:

```
utilize: use
utilization: use
facilitate: help
endeavour: try
endeavor: try
ameliorate: improve
expedite: hurry
commence: start
terminate: end
demonstrate: show
necessitate: need
methodology: method
functionality: feature
individual: person
subsequently: later
prior to: before
in order to: to
approximately: about
sufficient: enough
additional: more
initiate: start
finalize: finish
optimal: best
numerous: many
component: part
```

**AI failure mode:** LLMs treat polysyllabic Latinate diction as a politeness or
authority signal, and inflate uniformly rather than at points of precision.

- "We utilize a comprehensive methodology to facilitate optimal resource utilization." Four long words, zero added meaning; "we use a method to use resources well" carries the same claim.
- Nominalized chains: "the implementation of the initialization of the configuration" for "configuring at startup".
- Register-matching to the prompt: asked for a formal tone, the model raises syllable count instead of raising precision — exactly Orwell's "air of scientific impartiality to biased judgements".

**Named exceptions:**

1. **Term of art.** A defined technical term whose short synonym is not a synonym (idempotent, serializable, monotonic, deterministic, cardinality). No shorter word covers it.
2. **Identifier.** The long word is the literal name of a function, flag, field, error, or UI element and must match the artifact verbatim.
3. **Legal or normative force.** Standards vocabulary where the word is load-bearing (indemnify, warrant, MUST/SHALL per RFC 2119).
4. **Quotation.** Quoted source or code block.
5. **Disambiguation.** The short word is ambiguous in this document's context and the long word is not; the writer names the ambiguity.

**Fix move:** Apply the mapped substitute, then re-read the sentence for changed
meaning. If meaning changed, restore the long word and record which exception
applies.

---

### 3. `cut-what-cuts`

**Orwell's original:** "If it is possible to cut a word out, always cut it out."

**Restated rule:** Delete every span whose removal leaves the propositions,
obligations, and referents of the sentence unchanged; a word survives only by
carrying content, obligation, or a required repetition.

**Objective test:** Delete the span. Then ask: **has any proposition, any
normative obligation, any referent, or any required redundancy disappeared?** If
no → the span was a violation. This is a decidable question per span, and the
report is countable: `n_deletable_spans` and `words_removed / words_total`.

Five mechanizable sub-families, all from Orwell's OPERATORS OR VERBAL FALSE LIMBS
paragraph:

- **Light verb + nominalization** ("give rise to", "make a decision", "perform an analysis") → single verb. Orwell: "The keynote is the elimination of simple verbs."
- **Not-un formation.** Orwell's footnote 3 supplies the mnemonic: "A not unblack dog was chasing a not unsmall rabbit across a not ungreen field."
- **Compound prepositions** ("with respect to", "in view of", "by dint of", "the fact that") → single preposition or conjunction.
- **Noun construction for gerund.** Orwell: "by examination of instead of by examining".
- **Expletive openers and closers** ("there is/are … that", "it is X that", "greatly to be desired", "deserving of serious consideration").

**Mechanizable?** PARTIAL. The five families are fully mechanizable; general
cuttability is not, because only a reader can confirm no proposition was lost.
Split accordingly: Vale owns the families, the agentic reviewer owns the general
case. Starter regexes:

```
not[- ]un:            \bnot\s+un\w+
compound preps:       \b(?:with (?:respect|regard) to|having regard to|in view of|by dint of|in the interests? of|on the hypothesis that|in the event that|for the purpose of|in the process of|with the exception of|due to the fact that|in spite of the fact that|the fact that)\b
light verb + noun:    \b(?:make|give|perform|conduct|provide|achieve|effect|undertake|carry out|take)\s+(?:a|an|the)?\s*\w+(?:tion|sion|ment|ance|ence|ing|al|ysis)\b
expletive opener:     \b(?:There|It)\s+(?:is|are|was|were)\b(?=[^.?!]*\bthat\b)
verbal false limbs:   \b(?:render(?:s|ed)? inoperative|militate against|make contact with|be subjected to|give(?:s)? rise to|give(?:s)? grounds for|have the effect of|play(?:s|ed)? a leading (?:part|role) in|make(?:s)? itself felt|exhibit(?:s)? a tendency to|serve(?:s)? the purpose of)\b
anticlimax closers:   \b(?:greatly to be desired|cannot be left out of account|a development to be expected in the near future|deserving of serious consideration|brought to a satisfactory conclusion|a consideration which we should do well to bear in mind|a conclusion to which all of us would readily assent|leaves much to be desired|would serve no good purpose)\b
```

**AI failure mode:** LLM output is padded structurally, not accidentally. The
padding is the model's turn-taking and hedging behaviour leaking into prose.

- **Restating the prompt.** "It is important to note that when it comes to configuring the cache, there are several factors that should be considered." Zero propositions; deleting the whole sentence loses nothing.
- **Terminal summary paragraph.** A closing paragraph that re-asserts the section with no new predicate — "In summary, the approach described above provides a way to…".
- **Bilateral hedging.** "This may potentially help to somewhat reduce latency in certain cases." Four hedges stacked; either the claim has evidence (state it with the number) or it does not (delete it).

**Named exceptions:**

1. **Safety redundancy.** Deliberate repetition required by a safety-critical, legal, or operational procedure (see Conflicts, C3). Must be flagged as such in the document's front matter or by annotation.
2. **Normative keyword.** RFC 2119 / ISO keywords carrying obligation.
3. **Referential clarity.** The word disambiguates a pronoun or antecedent that would otherwise be ambiguous.
4. **Quotation and code.** Quoted text, code, log output, transcript, or config sample.
5. **Grammatical requirement.** Removal produces text that no longer parses.
6. **Prosody at a sentence boundary.** Bounded escape hatch: at most one per section, and it must be annotated. This is the narrowed remnant of Orwell's "avoidably ugly".

**Fix move:** Delete the span. Where the span was a light-verb construction,
promote the nominalization to a finite verb ("perform an analysis of" →
"analyse").

---

### 4. `active-unless-agentless`

**Orwell's original:** "Never use the passive where you can use the active."

**Restated rule:** Use the active voice whenever the actor is known, and use the
passive only under one of the four named agentless conditions, which the writer
must be able to name on request.

**Objective test:** Two steps, both decidable.

1. **Detect.** Is the clause passive? Countable: `n_passive_clauses / n_clauses`.
2. **Adjudicate.** Can the actor be named from this sentence or the sentence before it? If yes → violation; rewrite active. If no, which of the four conditions holds: (a) the actor is genuinely unknown, (b) the actor is any conforming implementation and naming one would over-specify, (c) the actor is the reader and naming them is wrong for the register (a spec describing what the system does to input), (d) the grammatical subject is the topic of the paragraph and moving it destroys the topic chain.

Condition (d) is the Duke resource's own carve-out; its site carries a dedicated
page, "Passive Voice in Scientific Writing", alongside the six rules, which is
evidence that the field treats blanket passive-avoidance as wrong.

**Mechanizable?** PARTIAL — and this is the split that matters most for false
positives. Detection is mechanizable; adjudication is not.

Detection regex (over-broad on purpose; every hit goes to the reviewer, none is
auto-failed):

```
\b(?:am|is|are|was|were|be|been|being|get|gets|got|gotten)\s+(?:\w+ly\s+)?(?:\w+(?:ed|en)|born|built|done|found|given|held|kept|known|made|put|read|run|seen|sent|set|shown|told|written)\b
```

Agent-present sub-case, which is always a violation because the actor is right
there:

```
\b(?:is|are|was|were|be|been|being)\s+(?:\w+ly\s+)?\w+(?:ed|en)\s+by\s+(?!default|design|convention|the time)\w+
```

**AI failure mode:** LLMs use the passive to avoid committing to an actor,
because non-commitment is rewarded in their training. Orwell's diagnosis of
euphemism applies verbatim: passive voice lets the model "name things without
calling up mental pictures of them".

- **Actor erasure in incident and status text.** "The outage was caused by a configuration change that was applied without review." Every actor is deleted; nothing is actionable.
- **Self-effacing process narration.** "The tests were run and improvements were made to the error handling." Who ran them, what improved, measured how.
- **Abstraction as actor** (the passive's sibling): "the complaint becomes a fix", "the requirement drives the design". No agent exists to hold responsible.

**Named exceptions:**

1. **Unknown actor.** No source identifies who or what acted.
2. **Any-implementation actor.** Specs and interface contracts: "the request is rejected with 400" holds for every conforming server.
3. **Reader-as-actor in reference material.** Register forbids "you"; the object is the topic.
4. **Topic-chain continuity.** Making the clause active would break the paragraph's given-before-new order.
5. **Quotation, code, and error strings.** Verbatim reproduction, including passive error messages.
6. **Established idiom of the artifact.** A standard or regulator mandates the passive phrasing.

**Fix move:** Name the actor and make it the grammatical subject. Where no actor
can be named, keep the passive and record which of the four conditions applies;
where the actor was deliberately omitted to soften a claim, that is a
`name-the-agent` violation (Rule 10) rather than a voice violation.

---

### 5. `plain-word-first`

**Orwell's original:** "Never use a foreign phrase, a scientific word, or a jargon word if you can think of an everyday English equivalent."

**MODERNIZED.** Two changes to Orwell's framing, each stated with its reason.

- **The "foreign phrase" clause is retired as written.** Orwell's own argument for it is register-based — such phrases "are used to give an air of culture and elegance" — and his examples are Latin, French, and German phrases functioning as class markers in 1946 English. Applied to a modern multilingual readership the clause reads as a proscription on non-English words, which is both xenophobic in effect and useless as a test. What survives is the *mechanism*, not the target: **a word chosen for the register it signals rather than the meaning it carries is a violation.** Orwell already carved out the abbreviations he found useful — "Except for the useful abbreviations i. e., e. g. and etc." — so a carve-out list is his own device.
- **The "scientific word" clause is re-aimed.** In 1946 "scientific" was the borrowed-authority register. Today the borrowed-authority registers are corporate-strategy diction, AI-industry diction, and technical vocabulary used outside its domain. Orwell's diagnosis transfers exactly: language used "to give an air of scientific impartiality to biased judgements".

**Restated rule:** Use the plain word unless the term is a defined term of art
with no plain equivalent; jargon borrowed for authority, and any word on the
corporate/AI filler list, is a violation.

**Objective test:** For each flagged term ask, in order:

1. Is it defined in this document, its glossary, or a normative reference it cites? If not → violation.
2. Does a plain-word substitute exist that preserves the denotation? If yes → violation. (Same denotation test as `short-word-first`; this rule catches the register motive, that one catches the length.)
3. Would the target reader, at the stated audience level, need to look it up? If yes and it is not defined at first use → violation.

Countable: `n_undefined_jargon_terms`, plus `undefined_terms / distinct_terms`.

**Mechanizable?** YES for the token lists, PARTIAL for the "defined term of art"
check, which needs a glossary source. Give Vale the lists; give the reviewer the
glossary cross-check.

```
\b(?:leverage|leveraging|synergy|synergies|holistic|paradigm|ideate|operationaliz(?:e|ing)|actionable|impactful|best[- ]in[- ]class|mission[- ]critical|end[- ]to[- ]end|world[- ]class|value[- ]add|core competenc(?:y|ies)|circle back|touch base|bandwidth(?= to)|table stakes|北)\b
```

(Separate rules, not one alternation, so that messages differ; see the token
lists below for the full sets.)

**AI failure mode:** LLM prose reaches for jargon at exactly the points where it
has no specific content, so jargon density is a proxy for hollowness.

- **Corporate filler as connective tissue.** "We leverage a holistic, end-to-end approach to operationalize observability across the stack." Every content word is a register marker.
- **AI-industry self-description.** "This agentic workflow orchestrates multi-modal reasoning to deliver robust, seamless outcomes." Unfalsifiable; no reader can tell what runs.
- **Domain term outside its domain.** "orthogonal" for "unrelated", "non-deterministic" for "unpredictable", "asymptotically" for "eventually", "delta" for "difference". Borrowed precision with no precision behind it.

**Named exceptions:**

1. **Defined term of art.** Defined at first use, or in a glossary, or in a cited normative reference; and no plain synonym exists.
2. **Identifier fidelity.** The term appears verbatim in code, an API, a CLI flag, a config key, a log line, or a UI label.
3. **Quotation.** Attributed quotation, code block, or transcript.
4. **Standard abbreviation.** Orwell's own list — i.e., e.g., etc. — plus abbreviations expanded at first use.
5. **Proper noun.** Product, standard, organization, protocol, or person name in any language.
6. **Non-English word with no English equivalent** that the document defines at first use. This is the deliberate replacement for Orwell's foreign-phrase blanket: the test is equivalence, never origin.

**Fix move:** Replace with the plain word. If the term is a genuine term of art,
define it at first use and keep it consistent thereafter — do not alternate
between the term and a paraphrase.

---

### 6. `named-exception-only`

**Orwell's original:** "Break any of these rules sooner than say anything outright barbarous."

**STRICTER THAN ORWELL — deliberately.** Orwell's sixth rule is an appeal to
taste; "outright barbarous" is not decidable, and in an automated pipeline an
undecidable override collapses the other five. It also, in his construction,
overrides *any* rule for *any* aesthetic reason. We keep the escape hatch and
narrow it to the closed exception lists already attached to rules 1-5 and 7-10.
Warrant for narrowing rather than deleting: Orwell states the rules are for the
case "when instinct fails", and he concedes "One could keep all of them and still
write bad English" — so the rules are not self-sufficient and some override must
exist. What cannot survive automation is an *unnamed* one.

**Restated rule:** Break a rule only by invoking one of that rule's named
exceptions in an inline annotation; an unannotated violation is a violation, and
"it reads better" is not an exception.

**Objective test:** For every finding suppressed, is there an annotation of the
form `<!-- orwell-allow: rule=<id> reason=<exception-name> -->` whose
`reason` appears in that rule's closed exception list? Countable:
`n_suppressions`, `n_invalid_suppressions` (reason absent or not on the list),
and `suppressions_per_1000_words`. A rising suppression rate is itself a
reviewable signal.

**Mechanizable?** Split, and the split is the honest answer:

- **YES** for the annotation contract. Whether an annotation exists, is well-formed, and names a listed exception is pure regex:

```
<!--\s*orwell-allow:\s*rule=(?<rule>[a-z-]+)\s+reason=(?<reason>[a-z-]+)\s*-->
```

- **NO** for whether invoking the exception was *correct*. **Judgement question:** *Would a competent reader, shown the compliant rewrite and the exception claimed, agree the rewrite loses meaning, obligation, or fidelity that the exception protects?* This is the agentic reviewer's one irreducible call, and it is the only place taste-adjacent reasoning is admitted — bounded to adjudicating a named claim rather than forming a free-floating opinion.

**AI failure mode:** Given a rule and an escape hatch, LLMs invoke the hatch to
preserve their default register rather than to protect meaning.

- **Blanket exception claims.** Annotating an entire document `reason=term-of-art` so that all jargon findings vanish.
- **Reason laundering.** Claiming `reason=safety-redundancy` for a padded summary paragraph.
- **Self-granted aesthetics.** "Kept for readability" or "kept for flow" — a re-import of Orwell's taste clause under a new name. Reject: not on any list.

**Named exceptions:** none. This rule has no escape hatch; that is what makes it
the terminal rule.

**Fix move:** Replace the annotation with the compliant rewrite, or replace the
reason with one that is on the list and defensible against the judgement
question. Where no listed reason fits, the writer opens an issue to amend the
exception list — the list changes by review, not by annotation.

---

## Rule 7 candidates

Each block is **EXTENSION** in the sense that it is not one of the six rules —
but each is warranted by a named passage of the essay that the six rules do not
reach. Four candidates. Discarded candidates and why are listed at the end.

---

### 7. `empty-evaluative-word` — EXTENSION

**Warrant in the essay:** the entire MEANINGLESS WORDS section. The gap is
precise: Rule 5 tells you to swap a jargon word for "an everyday English
equivalent", but Orwell's meaningless words *have no equivalent*, because they
"not only do not point to any discoverable object, but are hardly ever expected
to do so by the reader". They are also short and Anglo-Saxon ("dead", "living",
"human", "natural"), so rules 2 and 3 do not catch them either. Nothing in the
six rules touches this class.

**Restated rule:** Delete or replace every evaluative word whose negation the
reader would accept as a difference of opinion rather than a disagreement about
fact.

**Objective test:** Orwell's own test, stated as a procedure. Take the word W in
its sentence. Write the sentence with W negated or with W's opposite. Then ask:
**would a reader treat the two sentences as contradicting each other about a
checkable fact?** Orwell's demonstration — "The outstanding feature of Mr. X's
work is its living quality" versus "its peculiar deadness" — is that the reader
"accepts this as a simple difference opinion", where with "black and white … he
would see at once that language was being used in an improper way".

Second, countable test for the AI case: **for each evaluative adjective, does a
number, benchmark, feature list, or citation appear within the same sentence or
the one following?** Report `unsupported_evaluatives`.

**Mechanizable?** PARTIAL. Token detection is YES; the negation test is NO.
Practical split: Vale flags the token, the reviewer runs the negation test and
the evidence-proximity check.

```
\b(?:robust|powerful|comprehensive|seamless|scalable|flexible|intuitive|elegant|clean|modern|cutting[- ]edge|state[- ]of[- ]the[- ]art|blazingly fast|lightning[- ]fast|battle[- ]tested|production[- ]grade|enterprise[- ]grade|best practice|world[- ]class|significant|substantial|dramatic|vast|rich|deep|meaningful|thoughtful|careful|sophisticated)\b
```

**AI failure mode:** unsupported evaluation is the single most characteristic
defect of LLM prose, because the model is optimized for reader approval and
evaluative adjectives are the cheapest form of it.

- "A robust, scalable architecture with comprehensive test coverage." Three claims, zero numbers. Negate each: "a fragile, non-scalable architecture with patchy coverage" — the reader cannot check either version, which is Orwell's test failing.
- "This provides a significant performance improvement." Significant against what baseline, measured how.
- "We carefully considered the tradeoffs and chose a thoughtful design." Describes claimed effort, not the artifact.

**Named exceptions:**

1. **Quantified.** A number, benchmark result, or citation in the same sentence or the next one. "Robust" survives as "survives 10^6 malformed inputs without crashing" — at which point the adjective is redundant and rule `cut-what-cuts` removes it anyway.
2. **Defined term of art.** "Robust" in control theory, "significant" as a statistical result with the test and p-value named, "scalable" with the scaling dimension and limit stated.
3. **Quotation.** Attributed praise, user quote, review excerpt.
4. **Identifier.** The word is part of a name (`RobustScaler`, `--comprehensive`).

**Fix move:** Delete the adjective and state the fact that motivated it. If no
such fact exists, delete the sentence.

---

### 8. `image-collision` — EXTENSION

**Warrant in the essay:** two passages the six rules do not cover. In DYING
METAPHORS: "incompatible metaphors are frequently mixed, a sure sign that the
writer is not interested in what he is saying." And the diagnostic paragraph:
"The sole aim of a metaphor is to call up a visual image. When these images
clash — as in The Fascist octopus has sung its swan song, the jackboot is thrown
into the melting pot — it can be taken as certain that the writer is not seeing a
mental image of the objects he is naming; in other words he is not really
thinking." Rule 1 bars *stale* figures. A collision can be assembled from two
fresh figures, or from two dead ones that rule 1 explicitly permits, and rule 1
passes it.

**Restated rule:** Within a sentence, sustain at most one physical source
domain; do not combine figures whose literal pictures cannot co-exist.

**Objective test:** For each figurative span in the sentence, name its source
domain (liquid, combat, biology, machinery, navigation, construction, weather,
sport, cooking). **Can the named literal objects occupy one picture at one
moment?** Two distinct domains in one sentence is a finding; three is a
violation regardless of domain. Countable: `distinct_source_domains_per_sentence`.

**Mechanizable?** PARTIAL. Mechanizable half: tag each token in the metaphor
lists with a `domain:` field, then count distinct domains per sentence — pure
arithmetic once the lexicon is annotated, and it catches Orwell's own examples
(octopus = biology, swan song = biology-as-music, jackboot = combat, melting pot
= metallurgy). Non-mechanizable half: unlisted or novel figures. **Judgement
question:** *Draw the sentence as one picture. Does it draw?*

**AI failure mode:** LLM figures are retrieved per-clause without a global image,
so collisions are the norm rather than the accident.

- "This unlocks a foundational pillar that lets teams hit the ground running at scale." Lock, architecture, running, magnitude — four domains, no picture.
- "The rollout was a double-edged sword that snowballed into a perfect storm." Blade, snow, weather.
- "We need to move the needle on this by boiling the ocean of technical debt." Gauge, cooking, finance.

**Named exceptions:**

1. **Dead metaphor.** A lexicalized term whose literal sense is no longer active for readers does not count toward the domain tally (pipeline, branch, thread, stack, bottleneck, orphan, deadline).
2. **Domain term.** The colliding word is the technical name (a `pipeline` that `branches` is not a mixed metaphor in a CI document).
3. **Deliberate juxtaposition.** The collision is the point and the text says so within the same paragraph.
4. **Quotation.** Quoted source, including quoted bad writing.

**Fix move:** Keep the figure that carries the most information, delete the
others, and restate what they were carrying literally.

---

### 9. `concrete-floor` — EXTENSION

**Warrant in the essay:** the Ecclesiastes demonstration, which is the essay's
central exhibit and is not covered by any of the six rules. Orwell: "in the
middle the concrete illustrations — race, battle, bread — dissolve into the vague
phrases 'success or failure in competitive activities'." And earlier, as a
general law: "As soon as certain topics are raised, the concrete melts into the
abstract." Crucially, "success or failure in competitive activities" contains no
stale figure (rule 1 passes), no unusually long word (rule 2 passes), nothing
strictly cuttable (rule 3 passes), no passive (rule 4 passes), and no jargon or
foreign phrase (rule 5 passes). All six rules pass a sentence Orwell wrote as his
worst-case specimen. That is the gap.

**Restated rule:** Every claim must name at least one checkable particular — a
number, a named entity, a command, a file path, or a specific event — and an
abstraction may not stand in for a particular the writer possesses.

**Objective test:** Per paragraph, count **concrete referents**: numbers with
units, proper nouns, identifiers, file paths, commands, dated events, quoted
strings. A paragraph making a factual claim with zero concrete referents is a
violation. Orwell's own scoring of the pair — "The first sentence contains six
vivid images, and only one phrase … that could be called vague. The second
contains not a single fresh, arresting phrase" — is exactly this count.

Second test, for the substitution case: **does the writer possess a more specific
term than the one used?** If the source material names "race, battle, bread" and
the text says "competitive activities", that is a violation even though the
abstraction is accurate.

Auxiliary countable metric, also Orwell's: **syllables per word** (his 1.22 vs
2.37) and **Latin/Greek-rooted word count** (his "eighteen of those words are
from Latin roots, and one from Greek").

**Mechanizable?** PARTIAL. Mechanizable half: counting concrete referents per
paragraph is straightforward — `\d`, capitalized non-sentence-initial tokens,
backticked spans, path-shaped tokens — and so is flagging abstraction-bearing
suffixes at high density:

```
abstraction density:  \b\w+(?:tion|sion|ment|ness|ity|ance|ence|ism|ology)\b
zero-referent para:   (paragraph with no match for) (?:\d|`[^`]+`|/[\w./-]+|\b[A-Z][a-z]+[A-Z]\w*)
```

Non-mechanizable half: whether a *more specific* term was available. **Judgement
question:** *Name the actual thing. Did the text name it, or did it name the
category the thing belongs to?*

**AI failure mode:** the model has no particulars, so it generates the category.
This is the mechanism behind LLM confabulation-by-vagueness — the text is
unfalsifiable rather than false.

- "The system handles a variety of edge cases to ensure reliable operation across different environments." No case, no environment, no measure of reliability.
- "Several factors contribute to improved performance in typical workloads." Which factors, which workload, how much.
- Category-for-instance substitution: "an appropriate authentication mechanism" where the code uses OIDC with a 15-minute token; "recent versions" where the source says 2.4.1 and later.

**Named exceptions:**

1. **Genuinely general claim.** A statement about a whole class where naming an instance would mislead (a definition, an invariant, a theorem).
2. **Deliberate summary layer.** An abstract, TL;DR, or overview section that a following section makes concrete — the annotation must name the section that discharges it.
3. **Redaction.** The particular is withheld for security, privacy, or confidentiality, and the text says so.
4. **Quotation.** Quoted source.

**Fix move:** Replace the category with the instance from the source material. If
the writer has no instance, delete the claim rather than abstract it — an
abstraction is not a substitute for missing evidence.

---

### 10. `name-the-agent` — EXTENSION

**Warrant in the essay:** the euphemism passage, which the six rules do not
reach. "Defenceless villages are bombarded from the air … this is called
pacification"; "Millions of peasants are robbed of their farms … this is called
transfer of population"; "People are imprisoned for years without trial … this is
called elimination of unreliable elements". And the mechanism: "Such phraseology
is needed if one wants to name things without calling up mental pictures of
them." Rule 4 covers grammatical passive; euphemism is not grammatically passive
("this is called pacification" aside, "pacification" is an active-voice noun) and
"transfer of population" is a plain-English phrase rule 5 would pass. Rule 4
catches the syntax; nothing in the six catches the *substitution of a
harm-concealing name for the act*.

**Restated rule:** Name who did what to whom in any sentence reporting a failure,
harm, cost, or change of state; do not substitute a process noun for the act or
an abstraction for the actor.

**Objective test:** Three questions per sentence reporting a negative or
consequential event, all decidable:

1. **Who acted?** Is a person, team, service, or process named as grammatical subject or in an adjacent clause?
2. **What happened, literally?** If the sentence were rewritten with the literal event, would it read as materially worse? Orwell's test — "pacification" vs "villages are bombarded from the air". A gap in severity between the euphemism and the literal statement is the finding.
3. **Who bore it?** Is the affected party named?

Countable: `unattributed_consequence_sentences`.

**Mechanizable?** PARTIAL. Mechanizable half: detect abstraction-as-subject and
process-noun-as-event, plus a euphemism token list:

```
abstraction as actor:  ^(?:The\s+)?\w+(?:tion|sion|ment|ness|ity|ance|ence)\s+(?:becomes|drives|leads to|results in|creates|ensures|enables)\b
process noun event:    \b(?:rightsizing|realignment|transition|transformation|optimization|rationalization|restructuring|consolidation|attrition|deprecation|sunset(?:ting)?|wind[- ]down|reduction in force|headcount adjustment|regrettable attrition)\b
harm without actor:    \b(?:an? (?:issue|error|incident|outage|regression|defect)\s+(?:occurred|arose|was (?:identified|observed|introduced|encountered)))\b
```

Non-mechanizable half: whether a softer name was chosen over an available harder
one. **Judgement question:** *Write the sentence with the literal act and the
named actor. Is the rewrite materially worse for someone? If yes, the original
was a euphemism.*

**AI failure mode:** models are trained toward non-attribution and de-escalation,
so consequential text arrives actorless.

- "An issue was identified in the deployment pipeline and has since been addressed." No actor, no act, no impact. Orwell's structure exactly.
- "The complaint becomes a fix." An abstraction as actor; no one acted.
- "Following a period of organizational realignment, some roles were transitioned." Process noun for the act, passive for the actor, no affected party named.

**Named exceptions:**

1. **Blameless-postmortem convention.** Where the organization's stated policy is to name the *system* rather than the individual, the system must still be named — anonymity of a person is an exception, absence of an actor is not.
2. **Unknown actor.** No source identifies who acted; the text says the cause is unknown.
3. **Legal constraint.** Counsel or regulation forbids attribution, and the text says an attribution is withheld.
4. **Privacy.** Naming would identify a private individual without cause.
5. **Quotation.** Quoted source, including quoted euphemism under analysis.

**Fix move:** Rewrite as *actor — act — affected party*, using the literal name
of the act. Where an exception applies, keep the actor slot filled with the
narrowest nameable entity (team, service, policy) rather than deleting it.

---

### Candidates considered and rejected

Discipline note: the following were tempting but are not warranted as *separate*
rules by the essay, so they stay folded into existing rules.

| Rejected candidate | Why not a separate rule |
| --- | --- |
| `restore-the-verb` (light verb + nominalization) | Orwell's OPERATORS paragraph is real, but its remedy is word-deletion; it is fully served as a sub-family of `cut-what-cuts` with its own regex and message. A second rule would double-report the same span. |
| `no-not-un` | Orwell names it and gives a mnemonic, but it is one regex over one construction. Sub-family of `cut-what-cuts`. |
| `sentence-length` | The essay never proposes a length limit. Orwell's *good* specimen is a 49-word sentence. Inventing a limit would contradict his exhibit. |
| `no-hedging` | Not in the essay as such. The hedge-stacking failure is caught by `cut-what-cuts` (deletable) and `empty-evaluative-word` (unsupported). |
| `grammar-and-usage` | Explicitly disclaimed: "It has nothing to do with correct grammar and syntax, which are of no importance so long as one makes one's meaning clear". |
| `no-colloquialism` / register floor | Also disclaimed: "it is not concerned with fake simplicity and the attempt to make written English colloquial." |

---

## Tier assignment

Tiers: **strict** = technical documentation (reference, specs, API docs,
runbooks). **normal** = general writing held to a high bar (README, guides, PR
and release text, essays, ADRs). **relaxed** = loose writing with only
high-level readability rules kept (issue comments, internal notes, chat-adjacent
prose, drafts).

`E` = enforced at that tier. `A` = advisory (reported, non-blocking).
`—` = excluded.

| ID | strict | normal | relaxed | Relaxed-tier justification |
| --- | --- | --- | --- | --- |
| `stale-figure` | E | E | A | Kept advisory: a cliché in a note costs the reader nothing, but the token list is free to run and the signal is useful. |
| `short-word-first` | E | E | — | Excluded at relaxed: word choice in throwaway prose has no downstream reader, and the substitution map produces the most false positives of any rule. |
| `cut-what-cuts` | E | E | A | Kept advisory and narrowed to the padding families only: LLM-generated padding wastes the reader's attention even in a note, but general cuttability is not worth a draft author's time. |
| `active-unless-agentless` | A | E | — | **Advisory at strict**, which inverts the tier ordering on purpose — see Conflict C1; agentless passive is correct in specs, so enforcing it there manufactures noise. Excluded at relaxed because voice is not a comprehension barrier in short text. |
| `plain-word-first` | E | E | A | Kept advisory: jargon density is the best single proxy for empty text, so it earns its place even in loose writing, but term-of-art traffic is heaviest in informal technical notes. |
| `named-exception-only` | E | E | E | Enforced at every tier. It is the contract that makes the other rules auditable; an unnamed suppression at any tier defeats the ruleset. Cost is zero where nothing is suppressed. |
| `empty-evaluative-word` | E | E | A | Kept advisory: it is the highest-yield rule against LLM text at any tier, and the negation test is cheap to run in one's head. Not enforced because an unsupported adjective in a note is not a defect. |
| `image-collision` | E | E | — | Excluded at relaxed: it needs a domain-annotated lexicon and a picture test, which is the most expensive check per finding for the least harm in loose prose. |
| `concrete-floor` | E | E | A | Kept advisory: zero-referent paragraphs are the signature of a model with nothing to say, and the count is mechanical. Not enforced because notes legitimately gesture at things named elsewhere. |
| `name-the-agent` | E | E | E | **Enforced at every tier.** Actor erasure in an incident note, a status update, or a comment causes exactly the harm Orwell describes, and loose registers are where it hides. This is the one content rule that does not relax. |

Two deviations from a plain strict > normal > relaxed ordering, stated
explicitly:

1. `active-unless-agentless` is *advisory at strict and enforced at normal*.
   Specifications legitimately need the agentless passive; general prose does
   not. Ranking strict above normal here would be wrong.
2. `named-exception-only` and `name-the-agent` are enforced at relaxed. The first
   is the audit contract; the second guards attribution, which is the failure the
   essay treats as most serious.

---

## Conflicts with technical writing

### C1 — Rule 4 (avoid the passive) versus legitimate agentless passive

**The conflict.** Orwell: "Never use the passive where you can use the active."
Specification prose has no actor to name. "The request is rejected with 400" is
correct for every conforming implementation; "The server rejects the request with
400" over-specifies, and "You will receive a 400" mis-assigns the actor. Orwell's
own objection is narrower than his rule: in OPERATORS he complains that "the
passive voice is wherever possible used in preference to the active" — the
defect is *preference*, not use. The Duke resource that hosts the six rules also
hosts a separate page, "Passive Voice in Scientific Writing", which is direct
evidence that the field does not read rule 4 literally.

**Resolution we adopt.** Split detection from adjudication. Vale reports passive
clauses as advisory at strict tier with the passive-rate metric; a finding
escalates to a violation only when the actor is nameable from the sentence or its
predecessor. The `by`-agent sub-case (`is caused by X`) is always a violation
because the actor is present in the sentence and can be promoted to subject at no
cost. Passive rate is tracked as a ratio, not banned: a spec section above the
configured ceiling gets a document-level finding, not a per-sentence flood.

### C2 — Rule 2 (never use a long word) versus precise technical terms

**The conflict.** "Idempotent", "serializable", "monotonic", "eventual
consistency", "cardinality" have no short synonyms. Replacing them loses the
claim. Orwell anticipates this and rules against the naive reading himself: "Nor
does it even imply in every case preferring the Saxon word to the Latin one,
though it does imply using the fewest and shortest words that will cover one's
meaning." The operative clause is **that will cover one's meaning**.

**Resolution we adopt.** `short-word-first` fires only where a substitution-map
entry exists, never on syllable count alone. The map contains only pairs where
the substitution is denotation-preserving in all contexts ("utilize"→"use"), and
terms of art are never added to it. Syllables-per-word is reported as a
document metric for the `concrete-floor` rule, where it belongs, and never as a
per-word finding. A term of art used *outside its domain* is not covered by this
rule at all; it is a `plain-word-first` violation, because the defect is borrowed
authority rather than length.

### C3 — Rule 3 (cut a word if possible) versus safety-critical redundancy

**The conflict.** "If it is possible to cut a word out, always cut it out" is
false for text where a misread has physical or legal consequence. Runbooks repeat
the destructive step's object. Warnings restate the precondition already stated
in the prose. Legal text repeats a defined term rather than pronominalizing it,
because a pronoun creates an ambiguity a court would have to resolve. In each
case the removal *is* possible and *is* wrong.

**Resolution we adopt.** Redundancy becomes an exception that must be declared,
not discovered. A document sets `safety_critical: true` in front matter, or
annotates the span; inside that scope, repetition of a defined term, a
precondition, or an object of a destructive action is exempt. Outside that scope,
`cut-what-cuts` fires normally. Orwell's rule is preserved as the default because
the overwhelming majority of repetition in AI text is padding, not safety; the
exception is narrow, named, and auditable via `suppressions_per_1000_words`.

### C4 — Rule 1 (no figure you are used to seeing in print) versus standardized documentation phrasing

**The conflict.** Documentation deliberately reuses phrasing, because a reader
scanning twenty pages needs the same construction to mean the same thing.
"Returns", "raises", "deprecated in favour of", "see also" are figures or fixed
phrases that appear in every document by design. Orwell's rule, read literally,
condemns exactly the consistency that reference material depends on.

**Resolution we adopt.** Rule 1 is scoped to *figures of speech*, not to fixed
functional phrasing, and its exception list carries **dead metaphor** and
**domain term** for precisely this case. Orwell licenses this himself: a
metaphor "which is technically 'dead' … has in effect reverted to being an
ordinary word and can generally be used without loss of vividness." Structural
repetition of a documented phrase pattern is a `cut-what-cuts` question at most,
never a `stale-figure` finding.

### C5 — Rule 5 (no jargon where an everyday word exists) versus identifier fidelity

**The conflict.** Documentation must reproduce the artifact's own vocabulary
exactly. If the flag is `--utilize-cache`, the prose says `--utilize-cache`.
Paraphrasing an identifier into plain English makes the document wrong.

**Resolution we adopt.** The **identifier fidelity** exception is unconditional
and does not require annotation when the token appears inside backticks, a code
fence, or a link to the artifact. Outside code formatting, the annotation is
required — which has the useful side effect of pressuring writers to mark
identifiers as code.

### C6 — Rule 6's taste clause versus automated review

**The conflict.** "Break any of these rules sooner than say anything outright
barbarous" cannot be evaluated by a linter, and an LLM reviewer given this rule
will use it to protect its own defaults. Left as written, rule 6 nullifies rules
1-5 in an automated pipeline.

**Resolution we adopt.** Replace it with `named-exception-only`. The escape hatch
survives; the appeal to taste does not. The single judgement retained — *does the
compliant rewrite lose what the named exception protects* — is bounded to
adjudicating a claim the writer has already made in writing, which is reviewable
and auditable, unlike a free-standing aesthetic veto.

---

## Word and phrase lists

Every token Orwell names, transcribed from the essay, in Vale-pasteable form,
with a modern-equivalents list beside each 1946 list. Orwell's lists are
verbatim; the modern lists are **EXTENSION**, warranted by his own method —
"There is a long list of flyblown metaphors which could similarly be got rid of
if enough people would interest themselves in the job."

### L1 — Dying metaphors (Orwell, verbatim)

Source: DYING METAPHORS paragraph, plus the closing paragraph's additions
("jackboot, Achilles' heel, hotbed, melting pot, acid test, veritable inferno"),
plus the two he reports as already killed ("explore every avenue", "leave no
stone unturned"), plus his mixed-metaphor exhibits.

```yaml
tokens:
  - ring the changes on
  - take up the cudgel for
  - toe the line
  - tow the line
  - ride roughshod over
  - stand shoulder to shoulder with
  - play into the hands of
  - no axe to grind
  - grist to the mill
  - fishing in troubled waters
  - on the order of the day
  - Achilles' heel
  - swan song
  - hotbed
  - the hammer and the anvil
  - melting pot
  - acid test
  - veritable inferno
  - jackboot
  - explore every avenue
  - leave no stone unturned
  - lay the foundations
  - achieve a radical transformation
  - iron heel
  - bloodstained tyranny
  - free peoples of the world
```

Note on `iron resolution`: Orwell cites it as an *acceptable* dead metaphor.
It belongs on the allowlist, not here.

### L1M — Dying metaphors, modern equivalents — EXTENSION

The 2020s stale band, with the LLM-characteristic subset marked.

```yaml
tokens:
  - tip of the iceberg
  - double-edged sword
  - low-hanging fruit
  - move the needle
  - moving the needle
  - game changer
  - game-changing
  - paradigm shift
  - perfect storm
  - silver bullet
  - holy grail
  - north star
  - secret sauce
  - force multiplier
  - sea change
  - boil the ocean
  - drink from the firehose
  - herding cats
  - moving parts
  - moving target
  - shift left
  - single pane of glass
  - table stakes
  - at the end of the day
  - when it comes to
  - in today's fast-paced world
  - in today's rapidly evolving landscape
  - in the ever-changing world of
  - in the realm of
  - in the world of
  - navigate the complexities of
  - a testament to
  - stands as a testament to
  - unlock the power of
  - unlock the potential of
  - harness the power of
  - tapestry of
  - rich tapestry
  - delve into
  - dive deep into
  - deep dive
  - it's worth noting that
  - the beating heart of
  - the connective tissue between
  - a double click on
  - peel back the layers
  - the elephant in the room
  - hit the ground running
  - raise the bar
  - level the playing field
```

LLM-characteristic subset (highest precision against generated text): `in today's
rapidly evolving landscape`, `in the realm of`, `a testament to`, `tapestry of`,
`delve into`, `it's worth noting that`, `navigate the complexities of`, `unlock
the power of`, `harness the power of`.

### L2 — Verbal false limbs / operators (Orwell, verbatim)

```yaml
tokens:
  - render inoperative
  - militate against
  - make contact with
  - be subjected to
  - give rise to
  - give grounds for
  - have the effect of
  - play a leading part in
  - play a leading role in
  - make itself felt
  - take effect
  - exhibit a tendency to
  - serve the purpose of
  - with respect to
  - having regard to
  - the fact that
  - by dint of
  - in view of
  - in the interests of
  - on the hypothesis that
  - greatly to be desired
  - cannot be left out of account
  - a development to be expected in the near future
  - deserving of serious consideration
  - brought to a satisfactory conclusion
  - a consideration which we should do well to bear in mind
  - a conclusion to which all of us would readily assent
  - leaves much to be desired
  - would serve no good purpose
  - a not unjustifiable assumption
  - in my opinion it is not an unjustifiable assumption that
  - felt impelled
  - by examination of
```

Plus Orwell's named *formations*, which are regex rather than tokens:

```yaml
not_un:        \bnot\s+un\w+
ize_coinage:   \b\w{6,}(?:ize|ise)(?:s|d|ing)?\b
de_coinage:    \bde[a-z]{5,}(?:e|ed|ing|s)?\b
noun_for_gerund: \bby\s+\w+(?:tion|sion|ment)\s+of\b
```

Orwell's example coinages, cited as the pattern to reject:
`deregionalize`, `impermissible`, `extramarital`, `non-fragmentary`.

The simple verbs Orwell names as the targets these constructions displace —
useful as the substitution *right-hand side*: `break`, `stop`, `spoil`, `mend`,
`kill`. And the general-purpose verbs whose presence signals the construction:
`prove`, `serve`, `form`, `play`, `render`.

### L2M — Verbal false limbs, modern equivalents — EXTENSION

```yaml
tokens:
  - make a decision
  - reach a decision
  - perform an analysis
  - conduct an investigation
  - provide an explanation
  - give consideration to
  - take into consideration
  - carry out an evaluation
  - undertake a review
  - have an impact on
  - has the ability to
  - is able to
  - is in a position to
  - serves as a
  - acts as a
  - functions as a
  - plays a role in
  - plays a key role in
  - is responsible for
  - due to the fact that
  - in spite of the fact that
  - despite the fact that
  - in the event that
  - for the purpose of
  - in the process of
  - with the exception of
  - in terms of
  - on the basis of
  - in relation to
  - as a result of
  - in order to
  - prior to
  - subsequent to
  - at this point in time
  - it is important to note that
  - it should be noted that
  - it is worth mentioning that
  - needless to say
  - in conclusion
  - to summarize
  - that being said
  - with that said
  - it goes without saying
```

Substitution map form for the mechanizable subset:

```yaml
make a decision: decide
perform an analysis of: analyse
conduct an investigation into: investigate
provide an explanation of: explain
give consideration to: consider
has the ability to: can
is able to: can
due to the fact that: because
in spite of the fact that: although
in the event that: if
for the purpose of: to
in order to: to
prior to: before
subsequent to: after
at this point in time: now
in terms of: ""
```

### L3 — Pretentious diction (Orwell, verbatim)

Four sub-lists, kept separate because Orwell assigns each a distinct function.

Dress-up nouns and verbs — "used to dress up a simple statement and give an air
of scientific impartiality to biased judgements":

```yaml
tokens:
  - phenomenon
  - element
  - individual
  - objective
  - categorical
  - effective
  - virtual
  - basic
  - primary
  - promote
  - constitute
  - exhibit
  - exploit
  - utilize
  - eliminate
  - liquidate
```

Dignifying adjectives:

```yaml
tokens:
  - epoch-making
  - epic
  - historic
  - unforgettable
  - triumphant
  - age-old
  - inevitable
  - inexorable
  - veritable
```

Archaic war-glorifying vocabulary:

```yaml
tokens:
  - realm
  - throne
  - chariot
  - mailed fist
  - trident
  - sword
  - shield
  - buckler
  - banner
  - jackboot
  - clarion
```

Unnecessary Latinate substitutions — Orwell's own examples:

```yaml
tokens:
  - expedite
  - ameliorate
  - predict
  - extraneous
  - deracinated
  - clandestine
  - subaqueous
```

Non-English phrases Orwell lists. **Retained for historical completeness only.**
Per the modernization note under `plain-word-first`, this list is *not* shipped as
a Vale rule; the test is plain-equivalence, never word origin. Orwell's own
carve-out — "Except for the useful abbreviations i. e., e. g. and etc." — is
preserved as an allowlist.

```yaml
# NOT SHIPPED - retained to document Orwell's 1946 framing, which we reject
historical_only:
  - cul de sac
  - ancien regime
  - deus ex machina
  - mutatis mutandis
  - status quo
  - gleichschaltung
  - weltanschauung
allowlist:
  - i.e.
  - e.g.
  - etc.
```

Party-jargon list Orwell gives as an example of factional vocabulary
(`hyena`, `hangman`, `cannibal`, `petty bourgeois`, `these gentry`, `lackey`,
`flunkey`, `mad dog`, `White Guard`). **Not shipped**: it is a 1946 political
lexicon with no modern analogue that survives the objectivity requirement. Its
*mechanism* — in-group vocabulary substituting for argument — is caught by
`empty-evaluative-word`.

Orwell's flower-name footnote (`snapdragon`→`antirrhinum`,
`forget-me-not`→`myosotis`) is his illustration of the same reflex; not a token
list, but the clearest statement of the underlying test: "It is hard to see any
practical reason for this change of fashion".

### L3M — Pretentious diction, modern equivalents — EXTENSION

Corporate-strategy register:

```yaml
tokens:
  - leverage
  - leveraging
  - synergy
  - synergies
  - holistic
  - paradigm
  - ideate
  - operationalize
  - actionable
  - impactful
  - best-in-class
  - mission-critical
  - end-to-end
  - value-add
  - core competency
  - key differentiator
  - strategic imperative
  - stakeholder alignment
  - circle back
  - touch base
  - bandwidth
  - deliverable
  - learnings
  - ask (as noun)
  - spend (as noun)
  - solutioning
  - incentivize
  - right-size
  - double-click
  - socialize (a document)
  - net-net
  - going forward
```

AI-industry register:

```yaml
tokens:
  - agentic
  - multi-modal
  - foundation model
  - emergent capabilities
  - human-in-the-loop
  - alignment (undefined)
  - guardrails
  - hallucination-free
  - prompt engineering
  - context-aware
  - intelligent automation
  - AI-powered
  - AI-driven
  - next-generation
  - transformative
  - democratize
  - supercharge
  - turbocharge
  - revolutionize
  - reimagine
  - unlock
  - empower
  - elevate
  - amplify
  - streamline
  - seamlessly integrate
```

Latinate inflation, as a substitution map:

```yaml
utilize: use
utilization: use
facilitate: help
endeavour: try
commence: start
terminate: end
demonstrate: show
necessitate: need
methodology: method
functionality: feature
individual: person
subsequently: later
approximately: about
sufficient: enough
additional: more
initiate: start
finalize: finish
optimal: best
numerous: many
component: part
implement: build
architect: design
ascertain: find out
disseminate: send
aggregate: total
```

Technical terms used outside their domain — the modern equivalent of Orwell's
"strayed scientific words":

```yaml
tokens:
  - orthogonal
  - non-deterministic
  - asymptotically
  - delta
  - vector
  - quantum leap
  - exponentially
  - order of magnitude
  - bandwidth
  - signal-to-noise
  - entropy
  - impedance mismatch
  - idempotent
  - eventually consistent
```

These are terms of art *inside* their field and violations *outside* it. The Vale
rule needs a scope filter, or the rule ships advisory-only with the message "term
of art — confirm the domain".

### L4 — Meaningless words (Orwell, verbatim)

Art-criticism set — "strictly meaningless, in the sense that they not only do not
point to any discoverable object":

```yaml
tokens:
  - romantic
  - plastic
  - values
  - human
  - dead
  - sentimental
  - natural
  - vitality
  - living quality
```

Political set — words with "several different meanings which cannot be reconciled
with one another":

```yaml
tokens:
  - fascism
  - democracy
  - socialism
  - freedom
  - patriotic
  - realistic
  - justice
  - class
  - totalitarian
  - science
  - progressive
  - reactionary
  - bourgeois
  - equality
```

Orwell's own footnote example of a passage built entirely from this class is the
*Poetry Quarterly* extract ("catholicity of perception and image, strangely
Whitmanesque in range … an inexorably serene timelessness"), quoted in full in
the taxonomy section above. It is the reference specimen for the reviewer's
negation test.

### L4M — Meaningless words, modern equivalents — EXTENSION

Unsupported evaluatives. This is the highest-yield list against LLM text.

```yaml
tokens:
  - robust
  - powerful
  - comprehensive
  - seamless
  - scalable
  - flexible
  - intuitive
  - elegant
  - clean
  - modern
  - cutting-edge
  - state-of-the-art
  - blazingly fast
  - lightning-fast
  - battle-tested
  - production-grade
  - enterprise-grade
  - world-class
  - industry-leading
  - best practice
  - significant
  - substantial
  - dramatic
  - vast
  - rich
  - deep
  - meaningful
  - thoughtful
  - careful
  - sophisticated
  - innovative
  - simply
  - easily
  - effortlessly
  - naturally
  - obviously
  - clearly
  - of course
```

Contested abstractions — the modern analogue of Orwell's political set. Each has
multiple irreconcilable definitions and requires definition at first use:

```yaml
tokens:
  - alignment
  - safety
  - intelligence
  - reasoning
  - understanding
  - quality
  - performance
  - reliability
  - simplicity
  - ergonomics
  - developer experience
  - technical debt
  - clean code
  - idiomatic
  - overengineered
  - production-ready
  - enterprise
```

### L5 — Euphemism list — EXTENSION

Warranted by the pacification passage. Orwell's three examples first, verbatim:

```yaml
orwell_verbatim:
  - pacification
  - transfer of population
  - rectification of frontiers
  - elimination of unreliable elements
```

Modern analogues, process-noun-for-act:

```yaml
tokens:
  - rightsizing
  - realignment
  - reduction in force
  - headcount adjustment
  - regrettable attrition
  - restructuring
  - consolidation
  - transition (of a person)
  - offboarding
  - sunsetting
  - wind-down
  - deprecation without date
  - service degradation
  - unexpected behaviour
  - suboptimal outcome
  - learning opportunity
  - was addressed
  - has been remediated
  - an issue occurred
  - an error was encountered
  - impacted (as a euphemism for harmed)
  - data was accessed
  - unauthorized access occurred
  - collateral
  - kinetic action
  - enhanced interrogation
```

### L6 — Allowlist (dead metaphors and permitted forms)

Warranted directly: a dead metaphor "can generally be used without loss of
vividness", and Orwell's abbreviation carve-out.

```yaml
dead_metaphors_allowed:
  - iron resolution
  - deadline
  - bottleneck
  - pipeline
  - branch
  - root
  - tree
  - leaf
  - stack
  - heap
  - thread
  - handshake
  - orphan
  - daemon
  - cache
  - flush
  - hook
  - port
  - bridge
  - gateway
abbreviations_allowed:
  - i.e.
  - e.g.
  - etc.
```

### L7 — Reviewer metrics

Countable measures, each traceable to a passage in the essay.

| Metric | Warrant | Orwell's reference values |
| --- | --- | --- |
| syllables per word | "forty-nine words but only sixty syllables … thirty-eight words of ninety syllables" | good 1.22, bad 2.37 |
| Latin/Greek-rooted word count | "eighteen of those words are from Latin roots, and one from Greek" | 19 of 38 in the bad sentence |
| concrete referents per paragraph | "six vivid images, and only one phrase … that could be called vague" | good 6 images / 1 vague phrase |
| distinct metaphor source domains per sentence | "When these images clash" | 1 |
| negatives per N words | "uses five negatives in fifty three words. One of these is superfluous" | 5 / 53 flagged as a defect |
| passive clauses / total clauses | "the passive voice is wherever possible used in preference to the active" | ratio, not a ban |
| suppressions per 1000 words | our narrowing of rule 6 (EXTENSION) | monitored, no reference value |
| unsupported evaluatives | MEANINGLESS WORDS negation test (EXTENSION) | 0 |
| unattributed consequence sentences | pacification passage (EXTENSION) | 0 |

Orwell's six revision questions, verbatim, as the reviewer's final pass:

> "What am I trying to say? What words will express it? What image or idiom will make it clearer? Is this image fresh enough to have an effect? … Could I put it more shortly? Have I said anything that is avoidably ugly?"
