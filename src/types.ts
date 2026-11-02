export interface TaskFamily {
  name: string;
  description: string;
  solved: number;
  total: number;
  status: string;
}

export interface OverviewData {
  name: string;
  version: string;
  subtitle: string;
  lambenchScore: {
    certified: number;
    total: number;
    percentage: number;
    rank: string;
  };
  timeBudgetMechanism: {
    flag: string;
    default: string;
    description: string;
    limits: string[];
  };
  families: TaskFamily[];
  validationV250: any;
}

export interface TaskItem {
  id: string;
  name: string;
  fileName: string;
  content: string;
  solution: string;
  family: string;
  category: string;
  encoding: 'Church' | 'Scott' | 'Tuple' | 'Algebraic' | 'Algorithm';
  status: 'SOLVED' | 'ALGO_WALL';
  complexity: string;
  op: string;
  description: string;
  dateAdded: string;
  tags: string[];
}

export interface SynthesisReceipt {
  timestamp: string;
  sharedTimeBudget: boolean;
  totalTimeAllowanceMs: number;
  timeSpentMs: number;
  timeRemainingMs: number;
  phases: {
    conceptPhase: {
      budgetMs: number;
      spentMs: number;
      expansions: number;
      result: string;
    };
    rawFallbackPhase: {
      budgetMs: number;
      spentMs: number;
      expansions: number;
      result: string;
    };
  };
  compositionArity: number;
  mdlAstGain: number;
  regressionFreeDevCheck: boolean;
  normalFormVerified: boolean;
}

export interface SynthesisResult {
  taskId: string;
  status: string;
  solution: string;
  description: string;
  receipt: SynthesisReceipt;
}

export interface TestExecutionResult {
  target: string;
  command: string;
  success: boolean;
  exitCode: number;
  stdout: string;
  stderr: string;
  durationMs: number;
}

export interface LambdaEvalResult {
  initial: string;
  normalForm: string;
  isNormalForm: boolean;
  steps: string[];
  totalSteps: number;
}

export interface GeneratedImageItem {
  id: string;
  imageUrl: string;
  prompt: string;
  originalImageUrl?: string;
  model: string;
  aspectRatio: string;
  timestamp: string;
  isEdited?: boolean;
}
