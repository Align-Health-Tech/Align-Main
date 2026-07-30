/**
 * Design tokens ported from Align-Pilot-V2 (`src/lib/lilly/tokens.ts`).
 * The CSS-variable mirrors live in `app/globals.css` — keep both in sync.
 *
 * Pilot name -> local name, where they differ:
 *   bg -> patientBg, bgDeep -> patientBgDeep, ink2 -> inkSoft,
 *   mute -> muted, primaryHover -> primaryDark.
 * `lavender` and `dangerInk` are local additions with no pilot equivalent.
 */

export const TOKENS = {
  patientBg: "#ECEEF8",
  patientBgDeep: "#E3E6F4",
  surface: "#FFFFFF",
  ink: "#0D1B4B",
  inkSoft: "#3D4A72",
  muted: "#8A94B8",
  line: "#D8DCF0",
  lineSoft: "#EEF0FB",
  primary: "#5352CC",
  primaryDark: "#4342B8",
  primarySoft: "#ECEEF8",
  primaryLight: "#E8E8F9",
  primaryInk: "#3B3AA0",
  lavender: "#D0D1FF",
  teal: "#2AC3B0",
  tealSoft: "#E0F7F5",
  danger: "#E04F3A",
  dangerSoft: "#FDECE9",
  /** Darker red reserved for error *text* — the pilot's `danger` fails AA at 12-14px. */
  dangerInk: "#8E2E27",
  gold: "#F5A623",
  goldSoft: "#FEF3DC",
  shadowSm: "0 1px 3px rgba(13, 27, 75, .06), 0 2px 8px rgba(13, 27, 75, .04)",
  shadowMd: "0 4px 16px rgba(13, 27, 75, .1), 0 8px 24px rgba(13, 27, 75, .06)",
  shadowPrimary: "0 4px 16px rgba(83, 82, 204, .3)",
  r: { sm: 8, md: 12, lg: 16, xl: 22, pill: 999 },
} as const;

export type Token = keyof typeof TOKENS;
