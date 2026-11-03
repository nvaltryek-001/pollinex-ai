export type Role = "admin" | "researcher" | "user";

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  created_at: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface SpeciesResult {
  species: string;
  confidence: number;
  method: string;
  similarity?: number;
  reason?: string;
  candidates?: { species: string; vote_share: number }[];
  original_prediction?: string;
  original_confidence?: number | null;
}

export interface StageResult {
  stage: string;
  score: number;
  distribution: Record<string, number>;
  uncertain: boolean;
  cues: Record<string, number>;
  method: string;
  note: string;
}

export interface Readiness {
  category: string;
  confidence: number;
  label: string;
  species: string;
  stage: string;
  supporting_observations: string[];
  factors: { factor: string; effect: string; detail?: string; value?: number }[];
  uncertainty_warnings: string[];
  strategy: { mechanism: string; pollination_types: string[]; compatibility: string; recommendation: string; detail: string } | null;
  biological_limitations: string[];
  research_sources: string[];
  evidence_level: string | null;
  method: string;
}

export interface Flower {
  id: number;
  detection: { box: [number, number, number, number]; score: number; low_confidence: boolean; method: string };
  species: SpeciesResult;
  stage?: StageResult;
  structure?: {
    centre_region: { box: number[]; center: number[]; area_fraction_of_flower: number } | null;
    structures?: { structure: string; status: string; visible: boolean | null; detail: string }[];
    yellow_cluster_visible: boolean;
    yellow_fraction_in_centre?: number;
    method: string;
    structure_detection_available: boolean;
    note: string;
  };
  health?: { indicators: { type: string; value: number; threshold: number }[]; status: string; measurements?: Record<string, number>; note?: string };
  pose?: {
    center_px: number[];
    center_norm: number[];
    facing_estimate: string;
    facing_ratio: number;
    major_axis_angle_deg: number;
    alignment: { dx_px: number; dy_px: number; distance_px: number; guidance: string };
    note: string;
  };
  readiness?: Readiness;
}

export interface Scan {
  id: number;
  created_at: string;
  source: string;
  mode: string;
  status: string;
  detection_method: string;
  flower_count: number;
  latency_ms: number;
  warnings: string[];
  summary: {
    species_counts?: Record<string, number>;
    stage_counts?: Record<string, number>;
    readiness_counts?: Record<string, number>;
    low_confidence_count?: number | null;
    analysed_flowers?: number;
    model?: { detector_backend: string; detector_version: string };
  };
  image_url: string;
  image_width: number;
  image_height: number;
  plant_id: number | null;
  field_id: number | null;
  environment_id: number | null;
  flowers?: Flower[];
}

export interface LiveResult {
  image_size: [number, number];
  flower_count: number;
  detections: { box: [number, number, number, number]; score: number; low_confidence: boolean; species: string; species_confidence: number }[];
  latency_ms: number;
  warnings: string[];
}

export interface SpeciesKB {
  id: string;
  common_name: string;
  scientific_name: string;
  aliases: string[];
  flower_type: string;
  compatibility: string;
  pollination_types: string[];
  primary_mechanism: string;
  mechanism_detail: string;
  reproductive_characteristics: string;
  ready_stages: string[];
  approaching_stages: string[];
  past_stages: string[];
  visual_readiness_cues: string[];
  strategy: string;
  simulation_profile: Record<string, number | string | boolean>;
  evidence: string[];
  evidence_level: string;
  limitations: string[];
  reference_images: number;
}

export interface Simulation {
  id: number;
  species_id: string;
  status: string;
  params: Record<string, unknown>;
  result_summary: {
    released?: number;
    captured?: number;
    lost?: number;
    simulated_transfer_efficiency?: number;
    target_coverage?: number | null;
    alignment_error_mm?: number;
    mean_time_to_capture_s?: number | null;
    notes?: string[];
    disclaimer?: string;
    error?: string;
  };
  sim_version: string;
  created_at: string;
  completed_at: string | null;
  scan_id: number | null;
}

export interface Replay {
  id: number;
  species_id: string;
  params: Record<string, unknown>;
  summary: Simulation["result_summary"];
  disclaimer: string;
  frames: { t: number; p: [number, number, number][]; c: number[] }[];
  geometry: { anthers: [number, number, number][]; stigma: [number, number, number]; targets: [number, number, number][]; target_radius_mm: number };
}

export interface EnvRecord {
  id: number;
  observed_at: string;
  field_id: number | null;
  temperature_c: number | null;
  relative_humidity_pct: number | null;
  rain_mm_h: number | null;
  wind_kmh: number | null;
  observation: string;
  source: string;
  source_detail: Record<string, unknown>;
  created_at: string;
}

export interface FieldLoc { id: number; name: string; latitude: number | null; longitude: number | null; area_m2: number | null; notes: string; created_at: string }
export interface Plant { id: number; label: string; field_id: number | null; species_id: string | null; cultivar: string; planted_on: string | null; notes: string; created_at: string }
export interface PollinationRecord { id: number; method: string; performed_at: string; species_id: string | null; plant_id: number | null; scan_id: number | null; flowers_treated: number; outcome_observed: string | null; notes: string; created_at: string }

export interface Dashboard {
  totals: Record<string, number>;
  species_distribution: Record<string, number>;
  stage_distribution: Record<string, number>;
  readiness_distribution: Record<string, number>;
  simulations_by_species: Record<string, { runs: number; mean_simulated_transfer_efficiency: number }>;
  scans_per_day_30d: Record<string, number>;
  detection_methods_30d: Record<string, number>;
  recent_scans: Scan[];
  environment_trend_30d?: { day: string; temperature_c?: number; relative_humidity_pct?: number; rain_mm_h?: number; wind_kmh?: number; records: number }[];
  simulation_history?: { id: number; species_id: string; created_at: string; status: string; mode: string; efficiency: number | null }[];
  provenance: string;
  model_performance?: { source: string; mAP50: number; mAP50_95: number; generated_at: string };
}
