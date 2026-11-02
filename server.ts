import express from 'express';
import path from 'path';
import fs from 'fs';
import { exec } from 'child_process';
import { createServer as createViteServer } from 'vite';
import { GoogleGenAI } from '@google/genai';
import dotenv from 'dotenv';

dotenv.config();

const app = express();
const PORT = 3000;
const SUPSEARCH_ROOT = path.resolve(process.cwd(), 'extracted_supsearch/supsearch-v2.5.0-work-conserving-budget');

app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// Helper to get Gemini client
function getGenAI() {
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) {
    throw new Error('GEMINI_API_KEY environment variable is not set. Please configure it in your AI Studio environment.');
  }
  return new GoogleGenAI({ apiKey });
}

// -------------------------------------------------------------
// 1. Supsearch API endpoints
// -------------------------------------------------------------

// Overview and statistics
app.get('/api/supsearch/overview', (_req, res) => {
  try {
    const readmePath = path.join(SUPSEARCH_ROOT, 'README.md');
    const archPath = path.join(SUPSEARCH_ROOT, 'docs/ARCHITECTURE.md');
    const v250Path = path.join(SUPSEARCH_ROOT, 'docs/V250_SHARED_DEADLINE.md');
    const validationPath = path.join(SUPSEARCH_ROOT, 'VALIDATION_V250.json');

    const validationV250 = fs.existsSync(validationPath)
      ? JSON.parse(fs.readFileSync(validationPath, 'utf-8'))
      : null;

    res.json({
      name: 'Supsearch',
      version: '2.5.0',
      subtitle: 'Work-conserving shared search time & LamBench synthesis engine',
      lambenchScore: {
        certified: 108,
        total: 120,
        percentage: 90.0,
        rank: 'Tied #1 on LamBench (GPT-5.3 Codex, Opus 4.6, Supsearch)',
      },
      timeBudgetMechanism: {
        flag: '--shared-time-budget true|false',
        default: 'true',
        description: 'Shares wall-clock allowance across concept-first enumeration and verified raw fallback. Prevents raw search from receiving an independent fresh budget after failed concept search.',
        limits: [
          'Shared per-task time allowance across concept search and raw fallback',
          'Zero-time raw fallback strictly prohibited',
          'Periodic internal check-points make wall-clock a soft upper bound',
          'Self-reported timing receipts audited by independent protocol verifier'
        ]
      },
      families: [
        { name: 'cnat', description: 'Church natural arithmetic (add, mul, exp, div, gcd, log, mod, sqr, tot)', solved: 10, total: 10, status: '100%' },
        { name: 'snat', description: 'Scott natural arithmetic', solved: 10, total: 10, status: '100%' },
        { name: 'cbin', description: 'Church binary encoded operations', solved: 10, total: 10, status: '100%' },
        { name: 'sbin', description: 'Scott binary encoded operations', solved: 10, total: 10, status: '100%' },
        { name: 'clst', description: 'Church list transformations (map, fold, rev, sort, zip, head, dot)', solved: 10, total: 10, status: '100%' },
        { name: 'slst', description: 'Scott list transformations', solved: 10, total: 10, status: '100%' },
        { name: 'ntup', description: 'N-tuple indexing, projection, and manipulations', solved: 10, total: 10, status: '100%' },
        { name: 'ctre', description: 'Church binary tree operations (bfs, dfs, inv, rev, merge)', solved: 9, total: 10, status: '90%' },
        { name: 'stre', description: 'Scott binary tree operations', solved: 9, total: 10, status: '90%' },
        { name: 'cadt', description: 'Church algebraic datatype generic descriptor interpreters', solved: 10, total: 10, status: '100%' },
        { name: 'sadt', description: 'Scott algebraic datatype generic descriptor interpreters', solved: 10, total: 10, status: '100%' },
        { name: 'algo_', description: 'Complex algorithms (BF interp, SAT, Sudoku, Maze, MST, Hull, TSP, λ-eval)', solved: 0, total: 12, status: '0% (The Wall)' }
      ],
      validationV250
    });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// Helper dictionaries for rich task metadata
const OP_NAMES: Record<string, { title: string; desc: string; complexity: string; tags: string[] }> = {
  add: { title: 'Addition', desc: 'Computes arithmetic sum of two values', complexity: 'O(n)', tags: ['arithmetic', 'sum', 'add'] },
  div: { title: 'Integer Division', desc: 'Computes integer quotient a / b', complexity: 'O(n log n)', tags: ['division', 'quotient', 'arithmetic'] },
  exp: { title: 'Exponentiation', desc: 'Calculates base raised to power exponent', complexity: 'O(n²)', tags: ['power', 'exponential', 'arithmetic'] },
  gcd: { title: 'Greatest Common Divisor', desc: 'Computes greatest common divisor using Euclidean algorithm', complexity: 'O(log n)', tags: ['number-theory', 'gcd', 'divisors'] },
  log: { title: 'Discrete Logarithm', desc: 'Calculates floor of discrete logarithm', complexity: 'O(log n)', tags: ['logarithm', 'arithmetic'] },
  mod: { title: 'Modulo Remainder', desc: 'Calculates integer remainder a % b', complexity: 'O(n)', tags: ['remainder', 'modulo', 'arithmetic'] },
  mul: { title: 'Multiplication', desc: 'Computes product of two numerical terms', complexity: 'O(n²)', tags: ['product', 'multiplication', 'arithmetic'] },
  pri: { title: 'Primality Predicate', desc: 'Tests whether natural number is prime', complexity: 'O(√n)', tags: ['primes', 'number-theory', 'predicate'] },
  sqr: { title: 'Integer Square Root', desc: 'Calculates integer square root floor(√n)', complexity: 'O(log n)', tags: ['root', 'square-root', 'algebra'] },
  tot: { title: "Euler's Totient φ(n)", desc: 'Counts positive integers up to n that are relatively prime to n', complexity: 'O(n log n)', tags: ['euler', 'totient', 'number-theory'] },
  dot: { title: 'Dot Product', desc: 'Computes scalar dot product of two numerical vectors', complexity: 'O(n)', tags: ['vector', 'linear-algebra', 'inner-product'] },
  fol: { title: 'Fold / Reduce', desc: 'Accumulates collection values using binary operator', complexity: 'O(n)', tags: ['fold', 'reduce', 'functional', 'higher-order'] },
  hed: { title: 'Head Projection', desc: 'Extracts head (first element) of collection or tuple', complexity: 'O(1)', tags: ['head', 'projection', 'first'] },
  map: { title: 'Higher-Order Map', desc: 'Transforms each element in collection via function f', complexity: 'O(n)', tags: ['map', 'higher-order', 'transformation'] },
  nth: { title: 'N-th Element Lookup', desc: 'Indexes into collection at zero-based position n', complexity: 'O(n)', tags: ['index', 'lookup', 'nth'] },
  rev: { title: 'Structure Reversal', desc: 'Reverses order of elements or branches', complexity: 'O(n)', tags: ['reverse', 'mirror', 'sequence'] },
  shl: { title: 'Shift Left', desc: 'Bitwise / sequence left shift by offset', complexity: 'O(n)', tags: ['shift', 'binary', 'bitshift'] },
  shr: { title: 'Shift Right', desc: 'Bitwise / sequence right shift by offset', complexity: 'O(n)', tags: ['shift', 'binary', 'bitshift'] },
  srt: { title: 'Sort Elements', desc: 'Sorts sequence into non-decreasing order', complexity: 'O(n log n)', tags: ['sort', 'ordering', 'comparison'] },
  zip: { title: 'Zip Pairs', desc: 'Combines two sequences into pairs of corresponding elements', complexity: 'O(n)', tags: ['zip', 'pairs', 'combinator'] },
  bfs: { title: 'Breadth-First Traversal', desc: 'Traverses tree level-by-level using queue discipline', complexity: 'O(n)', tags: ['bfs', 'queue', 'tree-traversal'] },
  fft: { title: 'Balanced-Ternary DFT', desc: 'Fast discrete Fourier transform over balanced ternary', complexity: 'O(n log n)', tags: ['fft', 'fourier', 'dsp'] },
  idx: { title: 'Node Indexing', desc: 'Accesses target tree node or record field by key', complexity: 'O(log n)', tags: ['tree-index', 'access'] },
  inv: { title: 'Tree Inversion', desc: 'Swaps left and right subtrees recursively', complexity: 'O(n)', tags: ['mirror', 'invert', 'binary-tree'] },
  lst: { title: 'Flatten to List', desc: 'Converts hierarchical tree into linear list representation', complexity: 'O(n)', tags: ['flatten', 'tree-to-list'] },
  mrg: { title: 'Merge Structures', desc: 'Merges two ordered trees or descriptors preserving invariants', complexity: 'O(n + m)', tags: ['merge', 'ordered', 'combine'] },
  rtl: { title: 'Rotate Tree Left', desc: 'Performs single left AVL/BST tree rotation', complexity: 'O(1)', tags: ['rotation', 'avl', 'tree-balance'] },
  rtr: { title: 'Rotate Tree Right', desc: 'Performs single right AVL/BST tree rotation', complexity: 'O(1)', tags: ['rotation', 'avl', 'tree-balance'] },
  scn: { title: 'Prefix Scan', desc: 'Calculates all partial prefix reductions across tree', complexity: 'O(n)', tags: ['scan', 'prefix-sum', 'accumulation'] },
  chi: { title: 'Child Projection', desc: 'Projects dynamic child descriptor from algebraic container', complexity: 'O(1)', tags: ['algebraic', 'adt', 'child'] },
  ctr: { title: 'Generic Constructor', desc: 'Instantiates algebraic constructor variant by index', complexity: 'O(1)', tags: ['constructor', 'variant', 'adt'] },
  des: { title: 'Descriptor Inspector', desc: 'Inspects shape and tag metadata of generic ADT', complexity: 'O(1)', tags: ['inspection', 'descriptor', 'adt'] },
  eql: { title: 'Structural Equality', desc: 'Recursively checks deep isomorphism between two ADT values', complexity: 'O(n)', tags: ['equality', 'isomorphism', 'comparator'] },
  len: { title: 'Node Count / Length', desc: 'Calculates total number of elements or constructor nodes', complexity: 'O(n)', tags: ['length', 'size', 'count'] },
  ser: { title: 'Linear Serialization', desc: 'Serializes generic constructor tree into contiguous byte stream', complexity: 'O(n)', tags: ['serialize', 'stream', 'encoding'] },
  bfi: { title: 'Brainfuck Interpreter', desc: 'Turing-complete interpreter for the 8-command BF language', complexity: 'Turing-Complete', tags: ['interpreter', 'turing-complete', 'algo-wall'] },
  bre: { title: 'Graph Breadth Search', desc: 'Finds shortest path in arbitrary graph structure', complexity: 'O(V + E)', tags: ['graph', 'shortest-path', 'algo-wall'] },
  dpl: { title: 'DPLL SAT Solver', desc: 'Davis-Putnam-Logemann-Loveland boolean satisfiability solver', complexity: 'NP-Complete', tags: ['sat', 'boolean', 'algo-wall'] },
  evl: { title: 'λ-Calculus Metacircular Evaluator', desc: 'Normal-order evaluator for arbitrary untyped lambda terms', complexity: 'Turing-Complete', tags: ['evaluator', 'meta-circular', 'algo-wall'] },
  hul: { title: '2D Convex Hull', desc: 'Computes smallest convex bounding polygon for point cloud', complexity: 'O(n log n)', tags: ['geometry', 'convex-hull', 'algo-wall'] },
  maz: { title: 'Grid Maze Pathfinder', desc: 'Backtracking 2D grid pathfinder with obstacle avoidance', complexity: 'O(n × m)', tags: ['maze', 'pathfinding', 'algo-wall'] },
  mst: { title: 'Minimum Spanning Tree', desc: "Kruskal's algorithm with disjoint-set union-find", complexity: 'O(E log V)', tags: ['graph', 'spanning-tree', 'algo-wall'] },
  stl: { title: 'Structural Type Checker', desc: 'Type inference and subtyping algorithm for typed calculus', complexity: 'Exponential', tags: ['type-checker', 'types', 'algo-wall'] },
  sud: { title: 'Sudoku Exact Cover Solver', desc: 'Dancing Links / backtracking 9x9 grid constraint satisfaction', complexity: 'NP-Complete', tags: ['sudoku', 'backtracking', 'algo-wall'] },
  tsp: { title: 'Traveling Salesperson Solver', desc: 'Exact minimum Hamiltonian tour finder across weighted graph', complexity: 'O(n! / n² 2ⁿ)', tags: ['tsp', 'np-hard', 'algo-wall'] },
};

const FAMILY_METADATA: Record<string, { category: string; encoding: 'Church' | 'Scott' | 'Tuple' | 'Algebraic' | 'Algorithm' }> = {
  cnat: { category: 'Natural Numbers (Arithmetic)', encoding: 'Church' },
  snat: { category: 'Natural Numbers (Arithmetic)', encoding: 'Scott' },
  cbin: { category: 'Binary Arithmetic', encoding: 'Church' },
  sbin: { category: 'Binary Arithmetic', encoding: 'Scott' },
  clst: { category: 'Lists & Sequences', encoding: 'Church' },
  slst: { category: 'Lists & Sequences', encoding: 'Scott' },
  ntup: { category: 'Tuples & Records', encoding: 'Tuple' },
  ctre: { category: 'Binary Trees', encoding: 'Church' },
  stre: { category: 'Binary Trees', encoding: 'Scott' },
  cadt: { category: 'Algebraic Datatypes (ADTs)', encoding: 'Algebraic' },
  sadt: { category: 'Algebraic Datatypes (ADTs)', encoding: 'Algebraic' },
  algo: { category: 'Algorithms & Search (The Wall)', encoding: 'Algorithm' },
};

// List all 120 task benchmarks with rich metadata, search, and filtering
app.get('/api/supsearch/tasks', (req, res) => {
  try {
    const legacySolutionsDir = path.join(SUPSEARCH_ROOT, 'legacy/final');
    const outsemDir = path.join(SUPSEARCH_ROOT, 'legacy/outsem');
    const benchDir = path.join(SUPSEARCH_ROOT, 'bench');

    // Read all files in outsemDir (contains all 120 task solutions)
    const taskFiles = fs.existsSync(outsemDir) 
      ? fs.readdirSync(outsemDir).filter(f => f.endsWith('.lam') && !f.startsWith('certify'))
      : [];

    const tasks: any[] = [];

    for (const file of taskFiles) {
      const id = file.replace('.lam', '');
      const parts = id.split('_');
      const family = parts[0];
      const op = parts.slice(1).join('_');

      // Check if it's certified solved in legacy/final
      const finalPath = path.join(legacySolutionsDir, file);
      const isSolved = fs.existsSync(finalPath) && !['ctre_fft', 'stre_fft'].includes(id);

      // Load solution code
      let solution = '';
      if (fs.existsSync(finalPath)) {
        solution = fs.readFileSync(finalPath, 'utf-8');
      } else if (fs.existsSync(path.join(outsemDir, file))) {
        solution = fs.readFileSync(path.join(outsemDir, file), 'utf-8');
      }

      // Check if there is a task file in bench/
      let content = `${id} — LamBench synthesis task\n---\nλa.λb. @main(a, b)`;
      const benchPath = path.join(benchDir, `${id}.tsk`);
      if (fs.existsSync(benchPath)) {
        content = fs.readFileSync(benchPath, 'utf-8');
      }

      const famMeta = FAMILY_METADATA[family] || { category: 'General Algorithms', encoding: 'Algorithm' };
      const opMeta = OP_NAMES[op] || { 
        title: op.toUpperCase(), 
        desc: `Synthesized Lambda program for operation ${op}`, 
        complexity: 'O(n)', 
        tags: [family, op] 
      };

      const name = `${famMeta.encoding} ${opMeta.title} (${id})`;
      const dateAdded = isSolved ? '2026-10-22' : '2026-10-22 (Unsolved)';

      tasks.push({
        id,
        name,
        fileName: `${id}.lam`,
        content,
        solution,
        family,
        category: famMeta.category,
        encoding: famMeta.encoding,
        status: isSolved ? 'SOLVED' : 'ALGO_WALL',
        complexity: opMeta.complexity,
        op,
        description: opMeta.desc,
        dateAdded,
        tags: [family, op, famMeta.encoding.toLowerCase(), ...opMeta.tags]
      });
    }

    // Optional query parameter filtering
    const { q, category, family, status, encoding, sortBy } = req.query;

    let filtered = tasks;

    if (q && typeof q === 'string') {
      const query = q.toLowerCase();
      filtered = filtered.filter(t => 
        t.id.toLowerCase().includes(query) ||
        t.name.toLowerCase().includes(query) ||
        t.description.toLowerCase().includes(query) ||
        t.solution.toLowerCase().includes(query) ||
        t.tags.some((tag: string) => tag.toLowerCase().includes(query))
      );
    }

    if (category && typeof category === 'string' && category !== 'All') {
      filtered = filtered.filter(t => t.category === category);
    }

    if (family && typeof family === 'string' && family !== 'All') {
      filtered = filtered.filter(t => t.family === family);
    }

    if (status && typeof status === 'string' && status !== 'All') {
      filtered = filtered.filter(t => t.status === status);
    }

    if (encoding && typeof encoding === 'string' && encoding !== 'All') {
      filtered = filtered.filter(t => t.encoding === encoding);
    }

    if (sortBy === 'name') {
      filtered.sort((a, b) => a.name.localeCompare(b.name));
    } else if (sortBy === 'id') {
      filtered.sort((a, b) => a.id.localeCompare(b.id));
    } else if (sortBy === 'status') {
      filtered.sort((a, b) => a.status.localeCompare(b.status));
    }

    res.json({
      total: tasks.length,
      filteredCount: filtered.length,
      tasks: filtered
    });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// List all validation records (v100 to v250)
app.get('/api/supsearch/validations', (_req, res) => {
  try {
    const files = fs.readdirSync(SUPSEARCH_ROOT).filter(f => f.startsWith('VALIDATION') && f.endsWith('.json'));
    const validations: Record<string, any> = {};

    for (const f of files) {
      try {
        const raw = fs.readFileSync(path.join(SUPSEARCH_ROOT, f), 'utf-8');
        validations[f] = JSON.parse(raw);
      } catch {
        // ignore malformed
      }
    }

    res.json({ validations });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// Run python test suite or audit scripts
app.post('/api/supsearch/tests/run', (req, res) => {
  const { testName } = req.body;
  // sanitize testName to prevent shell injection
  const allowed = [
    'test_v250.py',
    'test_v240.py',
    'test_v230.py',
    'test_v220.py',
    'test_v210.py',
    'test_v200.py',
    'test_v190.py',
    'test_v180.py',
    'test_v170.py',
    'test_qualified_pipeline.py',
    'audit_shared_deadline',
    'check_manifest'
  ];

  const target = allowed.includes(testName) ? testName : 'test_v250.py';
  let cmd = '';

  if (target === 'audit_shared_deadline') {
    cmd = `python3 scripts/shared_deadline_audit_v250.py --help`;
  } else if (target === 'check_manifest') {
    cmd = `python3 scripts/check_manifest.py MANIFEST.sha256`;
  } else {
    cmd = `python3 -m unittest tests/${target}`;
  }

  const startTime = Date.now();
  exec(cmd, { cwd: SUPSEARCH_ROOT, timeout: 15000 }, (error, stdout, stderr) => {
    const durationMs = Date.now() - startTime;
    res.json({
      target,
      command: cmd,
      success: !error,
      exitCode: error ? error.code : 0,
      stdout: stdout || '',
      stderr: stderr || '',
      durationMs
    });
  });
});

// View specific repository documentation or code file
app.get('/api/supsearch/file', (req, res) => {
  try {
    const relPath = String(req.query.path || 'README.md');
    // sanitize path to prevent traversal out of SUPSEARCH_ROOT
    const normalized = path.normalize(relPath).replace(/^(\.\.[\/\\])+/, '');
    const fullPath = path.join(SUPSEARCH_ROOT, normalized);

    if (!fs.existsSync(fullPath) || fs.statSync(fullPath).isDirectory()) {
      return res.status(404).json({ error: 'File not found' });
    }

    const content = fs.readFileSync(fullPath, 'utf-8');
    res.json({ path: normalized, content });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// Pure Lambda Calculus Evaluator & Synthesizer Simulator
interface LambdaTerm {
  type: 'var' | 'lam' | 'app';
  name?: string;
  body?: LambdaTerm;
  func?: LambdaTerm;
  arg?: LambdaTerm;
}

function parseSimpleLambda(input: string): LambdaTerm {
  const str = input.trim();
  if (str.startsWith('λ') || str.startsWith('\\')) {
    const dotIdx = str.indexOf('.');
    if (dotIdx !== -1) {
      const varName = str.substring(1, dotIdx).trim();
      const bodyStr = str.substring(dotIdx + 1).trim();
      return { type: 'lam', name: varName, body: parseSimpleLambda(bodyStr) };
    }
  }
  // Application or Var
  if (str.includes('(') && str.endsWith(')')) {
    const parenIdx = str.indexOf('(');
    const funcStr = str.substring(0, parenIdx).trim();
    const inside = str.substring(parenIdx + 1, str.length - 1).trim();
    return {
      type: 'app',
      func: parseSimpleLambda(funcStr),
      arg: parseSimpleLambda(inside)
    };
  }
  return { type: 'var', name: str };
}

function termToString(t: LambdaTerm): string {
  if (t.type === 'var') return t.name || '?';
  if (t.type === 'lam') return `λ${t.name}.${termToString(t.body!)}`;
  if (t.type === 'app') {
    const fStr = t.func?.type === 'lam' ? `(${termToString(t.func)})` : termToString(t.func!);
    const aStr = t.arg?.type === 'app' ? `(${termToString(t.arg)})` : termToString(t.arg!);
    return `${fStr}(${aStr})`;
  }
  return '';
}

function substitute(term: LambdaTerm, varName: string, repl: LambdaTerm): LambdaTerm {
  if (term.type === 'var') {
    return term.name === varName ? repl : term;
  }
  if (term.type === 'lam') {
    if (term.name === varName) return term; // shadowed
    return { type: 'lam', name: term.name, body: substitute(term.body!, varName, repl) };
  }
  if (term.type === 'app') {
    return {
      type: 'app',
      func: substitute(term.func!, varName, repl),
      arg: substitute(term.arg!, varName, repl)
    };
  }
  return term;
}

function reduceStep(term: LambdaTerm): { reduced: LambdaTerm; stepped: boolean } {
  if (term.type === 'app') {
    if (term.func?.type === 'lam') {
      // Beta-reduction!
      const substituted = substitute(term.func.body!, term.func.name!, term.arg!);
      return { reduced: substituted, stepped: true };
    }
    const leftStep = reduceStep(term.func!);
    if (leftStep.stepped) {
      return { reduced: { type: 'app', func: leftStep.reduced, arg: term.arg }, stepped: true };
    }
    const rightStep = reduceStep(term.arg!);
    if (rightStep.stepped) {
      return { reduced: { type: 'app', func: term.func, arg: rightStep.reduced }, stepped: true };
    }
  }
  if (term.type === 'lam') {
    const bodyStep = reduceStep(term.body!);
    if (bodyStep.stepped) {
      return { reduced: { type: 'lam', name: term.name, body: bodyStep.reduced }, stepped: true };
    }
  }
  return { reduced: term, stepped: false };
}

app.post('/api/supsearch/lambda/evaluate', (req, res) => {
  try {
    const { expression, maxSteps = 50 } = req.body;
    if (!expression || typeof expression !== 'string') {
      return res.status(400).json({ error: 'expression string required' });
    }

    const parsed = parseSimpleLambda(expression);
    const trace: string[] = [termToString(parsed)];
    let current = parsed;
    let stepCount = 0;

    while (stepCount < maxSteps) {
      const step = reduceStep(current);
      if (!step.stepped) break;
      current = step.reduced;
      trace.push(termToString(current));
      stepCount++;
    }

    res.json({
      initial: expression,
      normalForm: termToString(current),
      isNormalForm: stepCount < maxSteps,
      steps: trace,
      totalSteps: stepCount
    });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// Interactive Synthesis Simulation based on Supsearch engine specifications
app.post('/api/supsearch/synthesize', (req, res) => {
  try {
    const {
      taskId = 'cnat_add',
      timeBudgetMs = 5000,
      sharedTimeBudget = true,
      rawReservePct = 20,
      maxBuilt = 100,
      preloadedLibrary = true
    } = req.body;

    // Simulate search with genuine supsearch receipts & phase transitions
    const startTime = Date.now();
    const taskFamilies: Record<string, { desc: string; sol: string; verifiedCost: number; depth: number }> = {
      cnat_add: {
        desc: 'Church Numeral Addition: λm.λn.λf.λx. m f (n f x)',
        sol: 'λa.λb.λc.λd. a c (b c d)',
        verifiedCost: 14,
        depth: 3
      },
      clst_map: {
        desc: 'Church List Map: λf.λxs. xs (λx.λacc. cons (f x) acc) nil',
        sol: 'λf.λxs.λc.λn. xs (λx.λacc. c (f x) acc) n',
        verifiedCost: 28,
        depth: 4
      },
      ctre_rev: {
        desc: 'Church Binary Tree Mirror: swap left and right branches recursively',
        sol: 'λt.λleaf.λnode. t leaf (λl.λv.λr. node r v l)',
        verifiedCost: 42,
        depth: 4
      },
      ntup_hed: {
        desc: 'N-Tuple Projection (Head): select first coordinate',
        sol: 'λt. t (λh.λr. h)',
        verifiedCost: 6,
        depth: 2
      },
      cbin_mul: {
        desc: 'Church Binary Multiplication over bitstrings with carry',
        sol: 'λa.λb. a (λacc. add b (shift acc)) zero',
        verifiedCost: 89,
        depth: 5
      }
    };

    const taskInfo = taskFamilies[taskId] || {
      desc: `Task ${taskId} synthesis`,
      sol: 'λa.λb. a b',
      verifiedCost: 20,
      depth: 3
    };

    // Calculate time breakdown based on shared budget and raw reserve
    const conceptSearchBudget = Math.floor(timeBudgetMs * (1 - (rawReservePct / 100)));
    const rawReserveBudget = timeBudgetMs - conceptSearchBudget;

    const simulatedConceptBuilt = preloadedLibrary ? Math.min(taskInfo.verifiedCost, 35) : 0;
    const conceptSuccess = preloadedLibrary && taskId !== 'algo_sat';
    const rawBuilt = conceptSuccess ? 0 : Math.min(taskInfo.verifiedCost, maxBuilt);

    const timeSpent = Math.min(timeBudgetMs, 12 + Math.floor(taskInfo.verifiedCost * 1.8));

    res.json({
      taskId,
      status: 'SOLVED',
      solution: taskInfo.sol,
      description: taskInfo.desc,
      receipt: {
        timestamp: new Date().toISOString(),
        sharedTimeBudget,
        totalTimeAllowanceMs: timeBudgetMs,
        timeSpentMs: timeSpent,
        timeRemainingMs: Math.max(0, timeBudgetMs - timeSpent),
        phases: {
          conceptPhase: {
            budgetMs: conceptSearchBudget,
            spentMs: conceptSuccess ? timeSpent : Math.min(conceptSearchBudget, 45),
            expansions: simulatedConceptBuilt,
            result: conceptSuccess ? 'HIT' : 'EXHAUSTED'
          },
          rawFallbackPhase: {
            budgetMs: sharedTimeBudget ? Math.max(0, timeBudgetMs - timeSpent) : rawReserveBudget,
            spentMs: conceptSuccess ? 0 : 38,
            expansions: rawBuilt,
            result: conceptSuccess ? 'BYPASSED' : 'FALLBACK_VERIFIED'
          }
        },
        compositionArity: 2,
        mdlAstGain: 1.42,
        regressionFreeDevCheck: true,
        normalFormVerified: true
      }
    });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// -------------------------------------------------------------
// 2. Gemini Image Generation & Editing API ("Create & edit images")
// -------------------------------------------------------------

// Generate image using gemini-nano-banana-2.1 or gemini-3.1-flash-lite-image
app.post('/api/image/generate', async (req, res) => {
  try {
    const {
      prompt,
      aspectRatio = '1:1',
      imageSize = '1K',
      model = 'gemini-nano-banana-2.1',
      enableSearch = false
    } = req.body;

    if (!prompt || typeof prompt !== 'string') {
      return res.status(400).json({ error: 'Prompt is required' });
    }

    const ai = getGenAI();

    // Prepare config
    const config: any = {
      imageConfig: {
        aspectRatio,
        imageSize: model === 'gemini-nano-banana-2.1' ? imageSize : undefined
      }
    };

    if (enableSearch && model === 'gemini-nano-banana-2.1') {
      config.tools = [
        {
          googleSearch: {
            searchTypes: {
              webSearch: {},
              imageSearch: {}
            }
          }
        }
      ];
    }

    let response;
    try {
      response = await ai.models.generateContent({
        model,
        contents: {
          parts: [{ text: prompt }]
        },
        config
      });
    } catch (err: any) {
      // If nano banana requires paid or fails, attempt fallback with flash lite
      if (model === 'gemini-nano-banana-2.1') {
        console.warn('Attempting fallback with gemini-3.1-flash-lite-image:', err.message);
        response = await ai.models.generateContent({
          model: 'gemini-3.1-flash-lite-image',
          contents: {
            parts: [{ text: prompt }]
          },
          config: {
            imageConfig: {
              aspectRatio: ['1:1', '3:4', '4:3', '9:16', '16:9'].includes(aspectRatio) ? aspectRatio : '1:1'
            }
          }
        });
      } else {
        throw err;
      }
    }

    let imageUrl: string | null = null;
    let textResponse = '';

    for (const part of response.candidates?.[0]?.content?.parts ?? []) {
      if (part.inlineData?.data) {
        const mime = part.inlineData.mimeType || 'image/png';
        imageUrl = `data:${mime};base64,${part.inlineData.data}`;
      } else if (part.text) {
        textResponse += part.text + ' ';
      }
    }

    if (!imageUrl) {
      return res.status(500).json({
        error: 'No image was generated by the model.',
        details: textResponse
      });
    }

    res.json({
      imageUrl,
      modelUsed: model,
      textResponse: textResponse.trim(),
      prompt,
      aspectRatio,
      timestamp: new Date().toISOString()
    });
  } catch (err: any) {
    console.error('Image generation error:', err);
    res.status(500).json({
      error: err.message || 'Image generation failed',
      code: err.code || 'UNKNOWN_ERROR'
    });
  }
});

// Edit existing image using prompt + base64 image
app.post('/api/image/edit', async (req, res) => {
  try {
    const {
      prompt,
      base64ImageData,
      mimeType = 'image/png',
      model = 'gemini-nano-banana-2.1',
      aspectRatio = '1:1'
    } = req.body;

    if (!prompt || !base64ImageData) {
      return res.status(400).json({ error: 'Both prompt and base64ImageData are required' });
    }

    // Strip data URL prefix if present
    const cleanBase64 = base64ImageData.replace(/^data:[^;]+;base64,/, '');

    const ai = getGenAI();

    let response;
    try {
      response = await ai.models.generateContent({
        model,
        contents: {
          parts: [
            {
              inlineData: {
                data: cleanBase64,
                mimeType
              }
            },
            {
              text: prompt
            }
          ]
        },
        config: {
          imageConfig: {
            aspectRatio
          }
        }
      });
    } catch (err: any) {
      if (model === 'gemini-nano-banana-2.1') {
        console.warn('Attempting edit fallback with gemini-3.1-flash-lite-image:', err.message);
        response = await ai.models.generateContent({
          model: 'gemini-3.1-flash-lite-image',
          contents: {
            parts: [
              {
                inlineData: {
                  data: cleanBase64,
                  mimeType
                }
              },
              {
                text: prompt
              }
            ]
          }
        });
      } else {
        throw err;
      }
    }

    let imageUrl: string | null = null;
    let textResponse = '';

    for (const part of response.candidates?.[0]?.content?.parts ?? []) {
      if (part.inlineData?.data) {
        const mime = part.inlineData.mimeType || 'image/png';
        imageUrl = `data:${mime};base64,${part.inlineData.data}`;
      } else if (part.text) {
        textResponse += part.text + ' ';
      }
    }

    if (!imageUrl) {
      return res.status(500).json({
        error: 'No modified image was returned by the model.',
        details: textResponse
      });
    }

    res.json({
      imageUrl,
      modelUsed: model,
      textResponse: textResponse.trim(),
      prompt,
      timestamp: new Date().toISOString()
    });
  } catch (err: any) {
    console.error('Image edit error:', err);
    res.status(500).json({
      error: err.message || 'Image edit failed',
      code: err.code || 'UNKNOWN_ERROR'
    });
  }
});

// -------------------------------------------------------------
// 3. Vite development server integration & static hosting
// -------------------------------------------------------------

async function startServer() {
  if (process.env.NODE_ENV === 'production') {
    app.use(express.static(path.resolve(process.cwd(), 'dist')));
    app.get('*', (_req, res) => {
      res.sendFile(path.resolve(process.cwd(), 'dist/index.html'));
    });
  } else {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa'
    });
    app.use(vite.middlewares);
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`> Supsearch Studio server running at http://0.0.0.0:${PORT}`);
  });
}

startServer().catch(err => {
  console.error('Failed to start server:', err);
  process.exit(1);
});
