"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Locale, PatientSex } from "../lib/contracts";
import {
  BODY_DIAGRAMS,
  bodyDiagramForFile,
  publicDiagramPath,
  regionLabel,
} from "../lib/body-regions";
import { COPY } from "../lib/locales";

type Props = {
  diagramFile?: string | null;
  highlightedRegionIds?: string[] | null;
  locale: Locale;
  patientSex: PatientSex | "";
  selected: string;
  onSelected: (regionId: string, diagramFile: string) => void;
};

export function BodyDiagram({
  diagramFile,
  highlightedRegionIds,
  locale,
  patientSex,
  selected,
  onSelected,
}: Props) {
  const eligible = useMemo(
    () =>
      BODY_DIAGRAMS.filter((entry) => {
        if (patientSex === "female") return !/\bMale\b/i.test(entry.file);
        if (patientSex === "male") return !/\bFemale\b/i.test(entry.file);
        return true;
      }),
    [patientSex],
  );
  const initial =
    bodyDiagramForFile(diagramFile) ??
    eligible.find((entry) => /Torso Front/i.test(entry.file)) ??
    eligible[0];
  const [activeFile, setActiveFile] = useState(initial?.file ?? "");
  const active =
    eligible.find((entry) => entry.file === activeFile) ?? eligible[0];
  const copy = COPY[locale];

  if (!active) return null;

  return (
    <div className="body-question">
      <label className="field-label" htmlFor="body-view">
        {copy.changeBodyView}
      </label>
      <select
        id="body-view"
        className="text-field body-view-select"
        value={active.file}
        onChange={(event) => {
          const nextFile = event.target.value;
          const nextEntry = eligible.find((entry) => entry.file === nextFile);
          setActiveFile(nextFile);
          if (!nextEntry?.regions.includes(selected)) {
            onSelected("", nextFile);
          }
        }}
      >
        {eligible.map((entry) => (
          <option key={entry.file} value={entry.file}>
            {entry.title.replace(/([a-z])([A-Z])/g, "$1 $2")}
          </option>
        ))}
      </select>
      <SvgCanvas
        key={active.file}
        file={active.file}
        regions={active.regions}
        highlighted={new Set(highlightedRegionIds ?? [])}
        selected={selected}
        onSelected={(regionId) => onSelected(regionId, active.file)}
        locale={locale}
        interactive
      />
      {selected ? (
        <p className="selected-region" aria-live="polite">
          <span>{copy.selectedRegion}</span>
          <strong>{regionLabel(selected, locale)}</strong>
        </p>
      ) : null}
    </div>
  );
}

export function ReadOnlyBodyDiagram({
  file,
  regionId,
}: {
  file: string;
  regionId: string;
}) {
  const entry = bodyDiagramForFile(file);
  if (!entry) return null;
  return (
    <SvgCanvas
      key={file}
      file={file}
      regions={entry.regions}
      highlighted={new Set()}
      selected={regionId}
      onSelected={() => undefined}
      locale="en"
      interactive={false}
    />
  );
}

function SvgCanvas({
  file,
  regions,
  highlighted,
  selected,
  onSelected,
  locale,
  interactive,
}: {
  file: string;
  regions: string[];
  highlighted: ReadonlySet<string>;
  selected: string;
  onSelected: (regionId: string) => void;
  locale: Locale;
  interactive: boolean;
}) {
  const hostRef = useRef<HTMLDivElement>(null);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState(false);
  const [hovered, setHovered] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void fetch(publicDiagramPath(file))
      .then((response) => {
        if (!response.ok) throw new Error("diagram");
        return response.text();
      })
      .then((svg) => {
        if (cancelled || !hostRef.current) return;
        hostRef.current.innerHTML = svg;
        const root = hostRef.current.querySelector("svg");
        if (root) {
          root.setAttribute("width", "100%");
          root.removeAttribute("height");
          root.setAttribute("role", "img");
          root.style.height = "100%";
          root.style.maxHeight = "430px";
        }
        setLoaded(true);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, [file]);

  useEffect(() => {
    if (!loaded || !hostRef.current) return;
    for (const id of regions) {
      const node = hostRef.current.querySelector<SVGPathElement>(
        `#${escapeCss(id)}`,
      );
      if (!node) continue;
      const fill =
        id === selected
          ? "#E63946"
          : highlighted.has(id)
            ? "#F4A261"
            : "transparent";
      node.setAttribute(
        "style",
        `fill:${fill};stroke:#1a1a1a;stroke-width:.7;pointer-events:${interactive ? "auto" : "none"};cursor:${interactive ? "pointer" : "default"};opacity:.92;transition:fill .12s`,
      );
    }
  }, [highlighted, interactive, loaded, regions, selected]);

  const regionFromTarget = useCallback(
    (target: EventTarget): string | null => {
      if (!(target instanceof Element)) return null;
      const path = target.closest("path");
      return path?.id && regions.includes(path.id) ? path.id : null;
    },
    [regions],
  );

  return (
    <div
      className="diagram-canvas"
      onPointerDown={(event) => {
        if (!interactive) return;
        const region = regionFromTarget(event.target);
        if (region) onSelected(region);
      }}
      onPointerMove={(event) =>
        setHovered(interactive ? regionFromTarget(event.target) : null)
      }
      onPointerLeave={() => setHovered(null)}
    >
      <div ref={hostRef} className="diagram-svg-host" />
      {!loaded && !error ? <div className="diagram-loading" /> : null}
      {error ? (
        <div className="inline-error">Could not load body diagram.</div>
      ) : null}
      {hovered ? (
        <span className="diagram-tooltip">{regionLabel(hovered, locale)}</span>
      ) : null}
    </div>
  );
}

function escapeCss(id: string): string {
  if (typeof CSS !== "undefined" && CSS.escape) return CSS.escape(id);
  return id.replace(/[^a-zA-Z0-9_-]/g, "_");
}
