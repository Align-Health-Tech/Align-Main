import bodyDiagramData from "./bodydiagram-list.json";
import { BODY_REGION_LABELS_KO } from "./body-region-labels.ko";
import { BODY_REGION_LABELS_ZH } from "./body-region-labels.zh";
import type { Locale } from "./contracts";

export type BodyDiagramEntry = {
  file: string;
  title: string;
  regions: string[];
};

export const BODY_DIAGRAMS =
  bodyDiagramData.bodydiagrams as BodyDiagramEntry[];

export function bodyDiagramForFile(
  file: string | null | undefined,
): BodyDiagramEntry | undefined {
  return BODY_DIAGRAMS.find((entry) => entry.file === file);
}

export function englishRegionLabel(regionId: string): string {
  return regionId
    .replace(/^Select_/, "")
    .replace(/_/g, " ")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/\b(Female|Male|Torso|Front|Back)\b/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

export function regionLabel(regionId: string, locale: Locale): string {
  if (locale === "ko") {
    return BODY_REGION_LABELS_KO[regionId] ?? englishRegionLabel(regionId);
  }
  if (locale === "zh") {
    return BODY_REGION_LABELS_ZH[regionId] ?? englishRegionLabel(regionId);
  }
  return englishRegionLabel(regionId);
}

export function publicDiagramPath(file: string): string {
  return `/bodydiagram/${encodeURIComponent(file)}`;
}
