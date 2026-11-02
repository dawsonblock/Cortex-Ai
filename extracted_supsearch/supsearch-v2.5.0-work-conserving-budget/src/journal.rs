//! Cooperative single-writer promotion journal with fail-closed recovery.
//!
//! This is NOT an authenticated audit log. A local administrator can rewrite
//! both ledger and concept library. External custody remains necessary.
use crate::bank;
use crate::term;
use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};

pub(crate) struct RunLock { path: PathBuf }

impl RunLock {
    pub(crate) fn acquire(ledger: &Path) -> Result<Self, String> {
        let path = ledger.with_extension("jsonl.lock");
        if path == ledger { return Err("invalid lock path".into()); }
        if let Some(dir) = path.parent().filter(|p| !p.as_os_str().is_empty()) {
            fs::create_dir_all(dir).map_err(|e| format!("create lock directory: {e}"))?;
        }
        let mut file = fs::OpenOptions::new().write(true).create_new(true).open(&path)
            .map_err(|e| format!("learning lock busy or unavailable ({}): {e}; do not delete after an unexamined crash", path.display()))?;
        let result = (|| -> Result<(), String> {
            writeln!(file, "pid={} (cooperative, local)", std::process::id()).map_err(|e| e.to_string())?;
            file.sync_all().map_err(|e| e.to_string())
        })();
        if let Err(e) = result { let _ = fs::remove_file(&path); return Err(e); }
        Ok(Self { path })
    }
}
impl Drop for RunLock { fn drop(&mut self) { let _ = fs::remove_file(&self.path); } }

#[derive(Debug, Clone, PartialEq, Eq)]
enum Scalar { Str(String), Literal(String) }

struct Parser<'a> { bytes: &'a [u8], i: usize }
impl<'a> Parser<'a> {
    fn new(s: &'a str) -> Self { Self { bytes: s.as_bytes(), i: 0 } }
    fn ws(&mut self) { while self.i < self.bytes.len() && self.bytes[self.i].is_ascii_whitespace() { self.i += 1; } }
    fn next(&mut self, token: u8) -> Result<(), String> {
        self.ws();
        if self.bytes.get(self.i) != Some(&token) { return Err("malformed journal JSON".into()); }
        self.i += 1;
        Ok(())
    }
    fn string(&mut self) -> Result<String, String> {
        self.next(b'"')?;
        let mut out = Vec::new();
        loop {
            let c = *self.bytes.get(self.i).ok_or("unterminated journal string")?;
            self.i += 1;
            match c {
                b'"' => return String::from_utf8(out).map_err(|_| "invalid UTF-8 journal string".into()),
                b'\\' => {
                    let escape = *self.bytes.get(self.i).ok_or("incomplete JSON escape")?;
                    self.i += 1;
                    match escape {
                        b'"' | b'\\' | b'/' => out.push(escape),
                        b'n' => out.push(b'\n'), b'r' => out.push(b'\r'), b't' => out.push(b'\t'),
                        b'b' => out.push(8), b'f' => out.push(12),
                        b'u' => {
                            let end = self.i.checked_add(4).ok_or("overflow")?;
                            let hex = self.bytes.get(self.i..end).ok_or("short Unicode escape")?;
                            let h = std::str::from_utf8(hex).map_err(|_| "bad Unicode escape")?;
                            let cp = u32::from_str_radix(h, 16).map_err(|_| "bad Unicode escape")?;
                            let code = char::from_u32(cp).ok_or("unsupported Unicode surrogate")?;
                            let mut buf = [0; 4];
                            out.extend_from_slice(code.encode_utf8(&mut buf).as_bytes());
                            self.i = end;
                        }
                        _ => return Err("invalid JSON escape".into()),
                    }
                }
                0..=31 => return Err("unescaped JSON control character".into()),
                _ => out.push(c),
            }
        }
    }
    // RFC 8259 number grammar: exclude +1, leading zeroes and non-finite floats.
    fn json_number(s: &str) -> bool {
        let b = s.as_bytes();
        let mut i = 0;
        if b.get(i).copied() == Some(b'-') { i += 1; }
        match b.get(i).copied() {
            Some(b'0') => i += 1,
            Some(b'1'..=b'9') => {
                i += 1;
                while matches!(b.get(i).copied(), Some(b'0'..=b'9')) { i += 1; }
            }
            _ => return false,
        }
        if b.get(i).copied() == Some(b'.') {
            i += 1;
            if !matches!(b.get(i).copied(), Some(b'0'..=b'9')) { return false; }
            while matches!(b.get(i).copied(), Some(b'0'..=b'9')) { i += 1; }
        }
        if matches!(b.get(i).copied(), Some(b'e' | b'E')) {
            i += 1;
            if matches!(b.get(i).copied(), Some(b'+' | b'-')) { i += 1; }
            if !matches!(b.get(i).copied(), Some(b'0'..=b'9')) { return false; }
            while matches!(b.get(i).copied(), Some(b'0'..=b'9')) { i += 1; }
        }
        i == b.len() && s.parse::<f64>().is_ok_and(|v| v.is_finite())
    }
    fn value(&mut self) -> Result<Scalar, String> {
        self.ws();
        if self.bytes.get(self.i) == Some(&b'"') { return Ok(Scalar::Str(self.string()?)); }
        let start = self.i;
        while let Some(&b) = self.bytes.get(self.i) {
            if b == b',' || b == b'}' || b.is_ascii_whitespace() { break; }
            self.i += 1;
        }
        let text = std::str::from_utf8(&self.bytes[start..self.i]).map_err(|_| "invalid JSON literal")?;
        let valid = matches!(text, "true" | "false" | "null") || Self::json_number(text);
        if !valid { return Err("unsupported or invalid journal JSON value".into()); }
        Ok(Scalar::Literal(text.to_owned()))
    }
    fn object(&mut self) -> Result<BTreeMap<String, Scalar>, String> {
        self.next(b'{')?;
        let mut fields = BTreeMap::new();
        self.ws();
        if self.bytes.get(self.i) == Some(&b'}') { self.i += 1; }
        else { loop {
            let key = self.string()?;
            self.next(b':')?;
            let val = self.value()?;
            if fields.insert(key, val).is_some() { return Err("duplicate journal JSON key".into()); }
            self.ws();
            match self.bytes.get(self.i) {
                Some(b',') => { self.i += 1; }
                Some(b'}') => { self.i += 1; break; }
                _ => return Err("invalid object delimiter".into()),
            }
        } }
        self.ws();
        if self.i != self.bytes.len() { return Err("trailing journal JSON bytes".into()); }
        Ok(fields)
    }
}
fn field_str<'a>(fields: &'a BTreeMap<String, Scalar>, k: &str) -> Result<&'a str, String> {
    match fields.get(k) { Some(Scalar::Str(v)) => Ok(v), _ => Err(format!("missing string field {k}")) }
}
fn field_usize(fields: &BTreeMap<String, Scalar>, k: &str) -> Result<usize, String> {
    match fields.get(k) {
        Some(Scalar::Literal(v)) => v.parse::<usize>().map_err(|_| format!("invalid integer field {k}")),
        _ => Err(format!("missing integer field {k}")),
    }
}

/// Refuses partial journal writes and inconsistencies before a new session.
/// Does not prove external custody, cryptographic authenticity, or science.
pub(crate) fn verify_history(path: &Path, concepts: &[bank::Concept]) -> Result<(), String> {
    if !path.exists() { return Ok(()); }
    let md = fs::symlink_metadata(path).map_err(|e| e.to_string())?;
    if !md.file_type().is_file() || md.len() > 8 * 1024 * 1024 { return Err("unsafe or oversized learning ledger".into()); }
    let bytes = fs::read(path).map_err(|e| e.to_string())?;
    if !bytes.is_empty() && !bytes.ends_with(b"\n") { return Err("truncated journal record (missing newline)".into()); }
    let data = String::from_utf8(bytes).map_err(|_| "invalid UTF-8 journal")?;
    let mut pending: Option<(String,String,usize)> = None;
    let mut latest: Option<(String,String,usize,usize)> = None;
    // The initial concepts predate this journal. Every subsequent promoted
    // concept must match the complete ordered suffix of the current library.
    let mut initial_baseline: Option<usize> = None;
    let mut promotions = Vec::<(String,String,usize)>::new();
    let mut session_active = false;
    let mut requires_completion = false;
    let mut known_names = BTreeSet::<String>::new();
    let mut session_expected: Option<usize> = None;
    let mut in_final = false;
    let mut seen_paired = false;
    for (line_no, line) in data.lines().enumerate() {
        if line.is_empty() || line.len() > 16384 { return Err(format!("line {}: missing or oversized event",line_no+1)); }
        let fields = Parser::new(line).object().map_err(|e| format!("line {}: {e}", line_no+1))?;
        let event = field_str(&fields,"event").map_err(|e| format!("line {}: {e}",line_no+1))?;
        match event {
            "start" => {
                if pending.is_some() { return Err("new session during incomplete promotion".into()); }
                if session_active && requires_completion {
                    return Err("new session after unfinished schema-v7 session".into());
                }
                let initial = field_usize(&fields,"initial_concepts")?;
                let schema = match fields.get("schema_version") {
                    Some(_) => field_usize(&fields,"schema_version")?,
                    None => 6, // Preserve legacy journal compatibility.
                };
                if let Some((_,_,_,previous)) = &latest {
                    if *previous != initial { return Err("new session baseline differs from preceding commit".into()); }
                }
                if let Some(base) = initial_baseline {
                    if base.checked_add(promotions.len()) != Some(initial) {
                        return Err("journal concept-count continuity violation".into());
                    }
                } else {
                    initial_baseline = Some(initial);
                }
                session_active = true;
                requires_completion = schema >= 7;
                session_expected = Some(initial);
                in_final = false;
                seen_paired = false;
            }
            "promotion_intent" => {
                if pending.is_some() || !session_active || session_expected.is_none() || in_final { return Err("nested/late/orphan promotion intent".into()); }
                let name = field_str(&fields,"name")?.to_owned();
                let body = field_str(&fields,"term")?.to_owned();
                let arity = field_usize(&fields,"arity")?;
                if name.is_empty() || body.is_empty() || !(1..=5).contains(&arity) || known_names.contains(&name) {
                    return Err("invalid or reused concept promotion".into());
                }
                pending = Some((name, body, arity));
            }
            "promotion_committed" => {
                let (name,body,arity) = pending.take().ok_or("commit without promotion intent")?;
                let count = field_usize(&fields,"concept_count")?;
                let expected = session_expected.ok_or("commit without session")?
                    .checked_add(1).ok_or("journal concept count overflow")?;
                if field_str(&fields,"name")? != name || count != expected {
                    return Err("commit name/count disagree with intent".into());
                }
                known_names.insert(name.clone());
                promotions.push((name.clone(), body.clone(), arity));
                latest = Some((name,body,arity,count));
                session_expected = Some(count);
            }
            "candidate_trial" | "train_attempt" | "curriculum_selection" | "no_promotion" | "dev_baseline_work" | "round_work" => {
                if !session_active || session_expected.is_none() || pending.is_some() || in_final {
                    return Err("training event outside learning phase".into());
                }
            }
            "final_test_paired" => {
                if !session_active || session_expected.is_none() || pending.is_some() || seen_paired {
                    return Err("duplicate or misplaced final evaluation".into());
                }
                seen_paired = true;
                in_final = true;
            }
            "final_test" => {
                if !session_active || !in_final || pending.is_some() { return Err("final row without paired final evaluation".into()); }
            }
            "session_completed" => {
                if !session_active || !requires_completion || pending.is_some() {
                    return Err("orphan or duplicate session completion".into());
                }
                if Some(field_usize(&fields,"concept_count")?) != session_expected {
                    return Err("session completion concept count differs from ledger".into());
                }
                session_active = false;
                requires_completion = false;
            }
            _ => return Err(format!("unknown journal event {event}")),
        }
    }
    if pending.is_some() { return Err("unreconciled promotion intent; investigate before resuming".into()); }
    if session_active && requires_completion {
        return Err("unfinished schema-v7 learning session; investigate crash before resuming".into());
    }
    let base = initial_baseline.ok_or("learning ledger has no start event")?;
    let total = base.checked_add(promotions.len()).ok_or("concept count overflow")?;
    if concepts.len() != total { return Err("journal concept count differs from library".into()); }
    for (actual, (name, body, arity)) in concepts[base..].iter().zip(promotions.iter()) {
        if actual.name != *name || actual.arity as usize != *arity || term::show(&actual.body) != *body {
            return Err("historical committed concept differs from library suffix".into());
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    fn sample(events: &str, concept_line: Option<&str>) -> Result<(),String> {
        let root = std::env::temp_dir().join(format!("supsearch-v110-{}-{:?}", std::process::id(),std::thread::current().id()));
        fs::create_dir_all(&root).unwrap();
        let journal = root.join("history.jsonl");
        fs::write(&journal, events).unwrap();
        let lib = root.join("library.tsv");
        if let Some(line) = concept_line { fs::write(&lib, line).unwrap(); }
        let concepts = crate::learning::load_library(&lib)?;
        let result = verify_history(&journal,&concepts);
        let _= fs::remove_dir_all(root);
        result
    }
    const START: &str = "{\"event\":\"start\",\"initial_concepts\":0}\n";
    #[test]
    fn json_parser_rejects_duplicates_and_forged_event_strings() {
        assert!(Parser::new("{\"event\":\"start\",\"event\":\"promotion_committed\"}").object().is_err());
        assert_eq!(field_str(&Parser::new(r#"{"message":"\"event\":\"promotion_committed\"","event":"promotion_intent"}"#).object().unwrap(),"event").unwrap(),"promotion_intent");
        assert!(Parser::new("{\"event\":\"start\"} extra").object().is_err());
        assert!(Parser::new("{\"event\":\"start\",\"x\":{}}").object().is_err());
        assert!(Parser::new(r#"{"event":"start","initial_concepts":01}"#).object().is_err());
        assert!(Parser::new(r#"{"event":"start","initial_concepts":+1}"#).object().is_err());
    }
    #[test]
    fn incomplete_promotion_cannot_be_hidden_in_other_field() {
        let event = concat!(r#"{"event":"promotion_intent","name":"c","arity":1,"term":"λa.a","note":"\"event\":\"promotion_committed\""}"#, "\n");
        assert!(sample(&(START.to_owned()+event),None).is_err());
    }
    #[test]
    fn validated_commit_requires_matching_library() {
        let events = format!("{START}{{\"event\":\"promotion_intent\",\"name\":\"concept_0001\",\"term\":\"λa.a\",\"arity\":1}}\n{{\"event\":\"promotion_committed\",\"name\":\"concept_0001\",\"concept_count\":1}}\n");
        assert!(sample(&events,Some("concept_0001\t1\tλa.a\n")).is_ok());
        assert!(sample(&events,Some("concept_0001\t1\tλa.λb.b\n")).is_err());
    }
    #[test]
    fn malformed_partial_and_unmatched_commits_rejected() {
        assert!(sample(&format!("{START}{{\"event\":\"promotion_committed\",\"name\":\"fake\",\"concept_count\":1}}\n"),None).is_err());
        assert!(sample(&format!("{START}{{\"event\":\"promotion_intent\""),None).is_err());
        assert!(sample("{\"event\":\"start\",\"initial_concepts\":0}",None).is_err());
    }
    #[test]
    fn full_committed_history_rejects_earlier_mutation_and_reorder() {
        let events = format!("{START}{{\"event\":\"promotion_intent\",\"name\":\"concept_0001\",\"term\":\"λa.a\",\"arity\":1}}\n{{\"event\":\"promotion_committed\",\"name\":\"concept_0001\",\"concept_count\":1}}\n{{\"event\":\"promotion_intent\",\"name\":\"concept_0002\",\"term\":\"λa.λb.b\",\"arity\":2}}\n{{\"event\":\"promotion_committed\",\"name\":\"concept_0002\",\"concept_count\":2}}\n");
        let good = "concept_0001\t1\tλa.a\nconcept_0002\t2\tλa.λb.b\n";
        let tampered = "concept_0001\t1\tλa.λb.a\nconcept_0002\t2\tλa.λb.b\n";
        let reordered = "concept_0002\t2\tλa.λb.b\nconcept_0001\t1\tλa.a\n";
        assert!(sample(&events,Some(good)).is_ok());
        assert!(sample(&events,Some(tampered)).is_err());
        assert!(sample(&events,Some(reordered)).is_err());
    }
    #[test]
    fn v7_rejects_unfinished_sessions_and_bad_terminal_count() {
        let start = "{\"event\":\"start\",\"schema_version\":7,\"initial_concepts\":0}\n";
        assert!(sample(start,None).is_err());
        let completed = format!("{start}{{\"event\":\"session_completed\",\"concept_count\":0}}\n");
        assert!(sample(&completed,None).is_ok());
        assert!(sample(&(completed.clone() + "{\"event\":\"session_completed\",\"concept_count\":0}\n"),None).is_err());
        assert!(sample(&format!("{start}{{\"event\":\"session_completed\",\"concept_count\":1}}\n"),None).is_err());
        assert!(sample(&(start.to_owned() + start),None).is_err());
    }
    #[test]
    fn v7_requires_terminal_before_another_session() {
        let start = "{\"event\":\"start\",\"schema_version\":7,\"initial_concepts\":0}\n";
        let done = "{\"event\":\"session_completed\",\"concept_count\":0}\n";
        assert!(sample(&(start.to_owned() + done + start + done),None).is_ok());
        assert!(sample(&(start.to_owned() + start + done),None).is_err());
    }
    #[test]
    fn lock_is_exclusive_and_released() {
        let root = std::env::temp_dir().join(format!("supsearch-lock-{}",std::process::id()));
        fs::create_dir_all(&root).unwrap();
        let journal = root.join("journal.jsonl");
        let first = RunLock::acquire(&journal).unwrap();
        assert!(RunLock::acquire(&journal).is_err());
        drop(first);
        assert!(RunLock::acquire(&journal).is_ok());
        let _ = fs::remove_dir_all(root);
    }
}
