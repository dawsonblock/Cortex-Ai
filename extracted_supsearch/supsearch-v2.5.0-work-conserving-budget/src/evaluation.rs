//! Explicit native evaluation interface. No concept discovery or promotion.
//! `raw` and `concept` modes are DIFFERENT search algorithms: compare like
//! with like for causal statements about concept promotion.
use crate::{bank, learning};
use std::{collections::BTreeSet, fs, path::PathBuf};

struct Config {
    directory: PathBuf, tasks: Vec<String>, library: PathBuf, out: PathBuf,
    mode: String, budget: f64, max_size: u32, fuel: i64, max_built: u64,
}

fn options(args: &[String]) -> Result<Config, String> {
    let mut c = Config {directory: PathBuf::from("bench"),tasks:Vec::new(),
        library:PathBuf::from("out/learning/concepts.tsv"),out:PathBuf::from("out/evaluation.jsonl"),
        mode:"concept".to_owned(),budget:1.0,max_size:13,fuel:20_000,max_built:0};
    let mut i=0;
    if args.first().is_some_and(|s| !s.starts_with("--")) {
        c.directory=PathBuf::from(&args[0]); i=1;
    }
    while i<args.len() {
        let flag=&args[i];
        let value=args.get(i+1).ok_or_else(|| format!("missing value for {flag}"))?;
        match flag.as_str() {
            "--tasks"=>c.tasks=value.split(',').map(str::trim).map(str::to_owned).collect(),
            "--library"=>c.library=PathBuf::from(value),
            "--out"=>c.out=PathBuf::from(value),
            "--mode"=>c.mode=value.clone(),
            "--budget"=>c.budget=value.parse().map_err(|_| "invalid budget")?,
            "--max-size"=>c.max_size=value.parse().map_err(|_| "invalid max-size")?,
            "--fuel"=>c.fuel=value.parse().map_err(|_| "invalid fuel")?,
            "--max-built"=>c.max_built=value.parse().map_err(|_| "invalid max-built")?,
            _=>return Err(format!("unknown evaluation argument: {flag}")),
        }
        i+=2;
    }
    if c.tasks.is_empty() || c.tasks.len()>200 || c.mode!="raw" && c.mode!="concept" ||
        !c.budget.is_finite() || c.budget<=0.0 || c.budget>3600.0 ||
        c.max_size<2 || c.max_size>64 || c.max_built>100_000_000 || c.fuel<=0 || c.fuel>10_000_000 {
            return Err("invalid evaluation settings".into());
        }
    let mut seen=BTreeSet::new();
    for id in &c.tasks {
        if id.is_empty() || !id.chars().all(|ch|ch.is_ascii_alphanumeric() || ch=='_' || ch=='-')
            || !seen.insert(id.clone()) {return Err("unsafe or duplicate task IDs".into());}
    }
    // Protect the output from overwriting a task or a concept library.
    if c.out==c.library {return Err("evaluation output collides with library".into());}
    if c.out.exists() {return Err("evaluation output already exists; use a fresh path".into());}
    for id in &c.tasks {
        if c.out==c.directory.join(format!("{id}.tsk")) {return Err("output collides with task".into());}
    }
    if c.out.components().any(|part|matches!(part,std::path::Component::ParentDir)) {
        return Err("evaluation output cannot contain parent traversal".into());
    }
    // Compare resolved paths after normalizing any existing ancestors. A
    // simple lexical check is insufficient for `./`, `../`, and symlink aliases.
    // Evaluation outputs must be outside the whole task tree, not merely avoid
    // overwriting the selected .tsk inputs. Never alter evaluator-held tasks.
    let canonical_tasks = fs::canonicalize(&c.directory)
        .map_err(|e| format!("task directory: {e}"))?;
    let output_parent = c.out.parent().filter(|p| !p.as_os_str().is_empty())
        .unwrap_or_else(|| std::path::Path::new("."));
    let mut ancestor = output_parent;
    while !ancestor.exists() {
        ancestor = ancestor.parent().ok_or("cannot resolve output parent")?;
    }
    let canonical_out_ancestor = fs::canonicalize(ancestor)
        .map_err(|e| format!("evaluation output ancestor: {e}"))?;
    let canonical_out_parent = canonical_out_ancestor.join(output_parent.strip_prefix(ancestor)
        .map_err(|_| "cannot resolve output path")?);
    if canonical_out_parent.starts_with(&canonical_tasks) {
        return Err("evaluation output must be outside task directory".into());
    }
    if let Ok(lib) = fs::canonicalize(&c.library) {
        if canonical_out_parent.join(c.out.file_name().ok_or("invalid output basename")?) == lib {
            return Err("evaluation output aliases concept library".into());
        }
    }
    Ok(c)
}
fn inner(args: &[String]) -> Result<(), String> {
    let c=options(args)?;
    let tasks=learning::load_tasks(&c.directory,&c.tasks)?;
    let concepts=if c.mode=="concept" {learning::load_library(&c.library)?} else {Vec::new()};
    let mut opts=bank::Options::default();
    opts.max_size=c.max_size;opts.time_budget_secs=c.budget;opts.fuel=c.fuel;opts.max_built=c.max_built;
    let mut output=String::new();
    output.push_str(&format!("{{\"event\":\"evaluation_meta\",\"schema_version\":5,\"mode\":\"{}\",\"concept_count\":{},\"task_count\":{},\"budget\":{},\"max_size\":{},\"fuel\":{},\"max_built\":{}}}\n",
        c.mode, concepts.len(),tasks.len(),c.budget,c.max_size,c.fuel,c.max_built));
    for (id, task) in &tasks {
        let result=if c.mode=="raw" {bank::solve(task,&opts)} else {bank::concept_solve(task,&concepts,&opts)};
        if let Some(solution) = result.solution.as_ref() {
            if !learning::solution_matches_examples(task, solution, c.fuel) {
                return Err(format!("{id}: solver returned an example-inconsistent solution"));
            }
        }
        output.push_str(&format!("{{\"event\":\"evaluation\",\"task\":{},\"mode\":\"{}\",\"solved\":{},\"built\":{},\"kept\":{},\"aborted\":{},\"elapsed_secs\":{:.9}}}\n",
            learning::json_escape(id),c.mode,result.solution.is_some(),result.stats.built,
            result.stats.kept,result.stats.aborted,result.stats.elapsed_secs));
    }
    learning::atomic_write_new(&c.out,output.as_bytes())?;
    println!("evaluated {} tasks with {} mode, {} concepts; results={}",tasks.len(),c.mode,concepts.len(),c.out.display());
    Ok(())
}
pub fn run(args:&[String]) {
    if let Err(e)=inner(args) {
        eprintln!("evaluate error: {e}\nusage: supsearch evaluate [task-dir] --tasks id,id --mode raw|concept --library FILE --out FILE [--budget 1] [--max-size 13] [--fuel 20000] [--max-built N]");
        std::process::exit(2);
    }
}
#[cfg(test)] mod tests {
    use super::*;
    #[test] fn rejects_more_than_200_tasks() {
        let ids = (0..201).map(|n|format!("task_{n}")).collect::<Vec<_>>().join(",");
        let args = vec!["--tasks".to_string(), ids];
        assert!(options(&args).is_err());
    }
    #[test] fn accepts_bounded_search_work() {
        let args=["bench","--tasks","cnat_add","--max-built","37"].map(str::to_owned);
        let cfg=options(&args).unwrap();
        assert_eq!(cfg.max_built,37);
        let invalid=["bench","--tasks","cnat_add","--max-built","100000001"].map(str::to_owned);
        assert!(options(&invalid).is_err());
    }
    #[test] fn state_cap_bounds_raw_search_and_concept_search() {
        let task=crate::parse::parse_task("test_id", "id\n---\nλa.@main(a)\n= λa.a\n").unwrap();
        let mut opts=crate::bank::Options::default();
        opts.max_size=4;
        opts.max_built=1;
        opts.time_budget_secs=1.0;
        let raw=crate::bank::solve(&task,&opts);
        let concept=crate::bank::concept_solve(&task,&[],&opts);
        assert!(raw.stats.built<=1);
        assert!(concept.stats.built<=1);
    }
    #[test] fn rejects_bad_mode() {
        let input=["--tasks","x","--mode","bad"].map(str::to_owned);
        assert!(options(&input).is_err());
    }
    #[test] fn rejects_duplicate_tasks() {
        let input=["--tasks","x,x"].map(str::to_owned);
        assert!(options(&input).is_err());
    }
    #[test] fn rejects_existing_output() {
        let p = std::env::temp_dir().join(format!("supsearch-04-eval-{}.jsonl", std::process::id()));
        fs::write(&p, "do not overwrite").unwrap();
        let args = ["--tasks".to_owned(), "x".to_owned(), "--out".to_owned(), p.to_string_lossy().into_owned()];
        assert!(options(&args).is_err());
        let _ = fs::remove_file(p);
    }
    #[test] fn rejects_output_nested_in_task_directory() {
        let input=["bench","--tasks","cnat_add","--out","bench/report/anything.jsonl"].map(str::to_owned);
        assert!(options(&input).is_err());
    }
    #[test] fn rejects_parent_traversal_in_output() {
        let input=["bench","--tasks","cnat_add","--out","scratch/../bench/leaked.jsonl"].map(str::to_owned);
        assert!(options(&input).is_err());
    }
    #[test] fn rejects_output_to_input() {
        let input=["bench","--tasks","x","--out","bench/x.tsk"].map(str::to_owned);
        assert!(options(&input).is_err());
    }
}
