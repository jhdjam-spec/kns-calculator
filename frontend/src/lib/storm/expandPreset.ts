// ╭───────────────────────────────────────────────────────────────────────╮
// │ INSERVO Studio — Калькулятор подбора КНС/НС/ЛОС                       │
// │ Автор: Константин Морозов · https://inservo.ru                        │
// │ Лицензия: MIT (см. LICENSE и NOTICE)                                  │
// │ Просьба сохранять авторство при использовании производных работ       │
// ╰───────────────────────────────────────────────────────────────────────╯
import presetsData from "@/data/objectTypePresets.json";

export type ObjectTypeId =
  | "parking"
  | "roof"
  | "carwash"
  | "industrial"
  | "cottage_village"
  | "warehouse_yard"
  | "road_section";

export type SpRevision = "SP_32_2012" | "SP_32_2018";

export interface ObjectTypePreset {
  id: ObjectTypeId;
  label: string;
  icon: string;
  short_description: string;
  surfaces: Record<string, number>;
  t_concentration_min: number;
  period_P_year: number;
  rationale: string;
  los_required: boolean;
  los_profile: string | null;
}

export interface SurfaceBreakdown {
  roof_ha: number;
  asphalt_ha: number;
  paving_dense_ha: number;
  paving_loose_ha: number;
  gravel_ha: number;
  crushed_stone_ha: number;
  soil_ha: number;
  lawn_ha: number;
  forest_ha: number;
  water_ha: number;
}

export interface MinimalStormInput {
  objectTypeId: ObjectTypeId;
  area_ha: number;
  region_city: string;
}

export interface FullStormCalcRequest {
  sp_revision: SpRevision;
  region_city: string;
  surfaces: SurfaceBreakdown;
  period_P_year: number;
  pipe_total_length_m?: number;
  pipe_velocity_mps?: number;
  t_concentration_min: number;
}

const presets = presetsData.presets as unknown as ObjectTypePreset[];

export function getPreset(id: ObjectTypeId): ObjectTypePreset {
  const preset = presets.find((p) => p.id === id);
  if (!preset) {
    throw new Error(`Unknown object type: ${id}`);
  }
  return preset;
}

export function listPresets(): ObjectTypePreset[] {
  return presets;
}

const EMPTY_SURFACES: SurfaceBreakdown = {
  roof_ha: 0,
  asphalt_ha: 0,
  paving_dense_ha: 0,
  paving_loose_ha: 0,
  gravel_ha: 0,
  crushed_stone_ha: 0,
  soil_ha: 0,
  lawn_ha: 0,
  forest_ha: 0,
  water_ha: 0,
};

const SHARE_TO_FIELD: Record<string, keyof SurfaceBreakdown> = {
  roof_share: "roof_ha",
  asphalt_share: "asphalt_ha",
  concrete_share: "asphalt_ha", // бетон считаем как асфальт для упрощения
  paving_dense_share: "paving_dense_ha",
  paving_loose_share: "paving_loose_ha",
  gravel_share: "gravel_ha",
  crushed_stone_share: "crushed_stone_ha",
  soil_share: "soil_ha",
  lawn_share: "lawn_ha",
  forest_share: "forest_ha",
  water_share: "water_ha",
};

/**
 * Развернуть Минимальный input в полный StormCalc-запрос.
 * Использует пресет для распределения поверхностей и параметров СП 32.
 */
export function expandPreset(input: MinimalStormInput): FullStormCalcRequest {
  const preset = getPreset(input.objectTypeId);
  const surfaces: SurfaceBreakdown = { ...EMPTY_SURFACES };

  for (const [shareKey, share] of Object.entries(preset.surfaces)) {
    const field = SHARE_TO_FIELD[shareKey];
    if (!field) continue;
    surfaces[field] = (surfaces[field] || 0) + input.area_ha * share;
  }

  return {
    sp_revision: presetsData.sp_revision_default as SpRevision,
    region_city: input.region_city,
    surfaces,
    period_P_year: preset.period_P_year,
    t_concentration_min: preset.t_concentration_min,
  };
}

/**
 * Утилита: м² → га.
 */
export function m2ToHa(m2: number): number {
  return m2 / 10000;
}

/**
 * Утилита: га → м².
 */
export function haToM2(ha: number): number {
  return ha * 10000;
}
