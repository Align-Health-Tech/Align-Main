/**
 * Korean labels for body-diagram path IDs. Keyed by the canonical SVG path id
 * from `apps/align-frontend/src/components/bodydiagram/bodydiagram_list.json`.
 *
 * Anatomical labels are intentionally medical-Korean (e.g. 견갑골 for
 * shoulder blade, 승모근 for trapezius) so they read naturally to native
 * Korean speakers while still being clinically precise. Translations are
 * subject to the native-reviewer pass tracked in `docs/korean/patch-ko.review.md`.
 *
 * Path IDs not covered here fall back to the procedural English label via
 * `bodyDiagramRegionLabelLocalised(...)` — see body-diagram-region-label-localised.ts.
 */
export const BODY_REGION_LABELS_KO: Readonly<Record<string, string>> = {
  // Arm — left back
  Select_LeftHand: "왼손",
  Select_LeftWrist: "왼손목",
  Select_LeftForearm: "왼팔뚝(전완)",
  Select_LeftTricep: "왼쪽 삼두근",
  Select_LeftShoulder: "왼쪽 어깨",
  // Arm — left front
  Select_LeftBicep: "왼쪽 이두근",
  // Arm — right
  Select_RightHand: "오른손",
  Select_RightWrist: "오른손목",
  Select_RightForearm: "오른팔뚝(전완)",
  Select_RightTricep: "오른쪽 삼두근",
  Select_RightShoulder: "오른쪽 어깨",
  Select_RightBicep: "오른쪽 이두근",

  // Face
  Select_Neck: "목",
  Select_LeftEar: "왼쪽 귀",
  Select_RightEar: "오른쪽 귀",
  Select_Chin: "턱",
  Select_Mouth: "입",
  Select_Nose: "코",
  Select_LeftEye: "왼쪽 눈",
  Select_RightEye: "오른쪽 눈",
  Select_LeftSide: "왼쪽 얼굴",
  Select_RightSide: "오른쪽 얼굴",
  Select_Forehead: "이마",

  // Female legs — back
  Select_FemaleLegs_Back_Right_LowerCalf: "오른쪽 아래 종아리",
  Select_FemaleLegs_Back_Left_LowerCalf: "왼쪽 아래 종아리",
  Select_FemaleLegs_Back_Right_Calf: "오른쪽 종아리",
  Select_FemaleLegs_Back_Left_Calf: "왼쪽 종아리",
  Select_FemaleLegs_Back_Right_BackofKnee: "오른쪽 오금(무릎 뒤)",
  Select_FemaleLegs_Back_Left_BackofKnee: "왼쪽 오금(무릎 뒤)",
  Select_FemaleLegs_Back_Right_Hamstring: "오른쪽 햄스트링",
  Select_FemaleLegs_Back_Left_Hamstring: "왼쪽 햄스트링",
  // Female legs — front
  Select_FemaleLegs_Front_LeftAnkle: "왼쪽 발목",
  Select_FemaleLegs_Front_RightAnkle: "오른쪽 발목",
  Select_FemaleLegs_Front_LeftFoot: "왼쪽 발",
  Select_FemaleLegs_Front_RightFoot: "오른쪽 발",
  Select_FemaleLegs_Front_LeftShin: "왼쪽 정강이",
  Select_FemaleLegs_Front_RightShin: "오른쪽 정강이",
  Select_FemaleLegs_Front_LeftKnee: "왼쪽 무릎",
  Select_FemaleLegs_Front_RightKnee: "오른쪽 무릎",
  Select_FemaleLegs_Front_Left_InnerThigh: "왼쪽 안쪽 허벅지",
  Select_FemaleLegs_Front_Right_InnerThigh: "오른쪽 안쪽 허벅지",
  Select_FemaleLegs_Front_Left_OuterThigh: "왼쪽 바깥 허벅지",
  Select_FemaleLegs_Front_Right_OuterThigh: "오른쪽 바깥 허벅지",

  // Female torso — back
  Select_Female_TorsoBack_Right_Lateral_LowerBack: "오른쪽 옆 허리(외측 하부)",
  Select_Female_TorsoBack_Left_Lateral_LowerBack: "왼쪽 옆 허리(외측 하부)",
  Select_Female_TorsoBack_Right_Lats: "오른쪽 광배근",
  Select_Female_TorsoBack_Left_Lats: "왼쪽 광배근",
  Select_Female_TorsoBack_Right_Medial_LowerBack: "오른쪽 안쪽 허리(내측 하부)",
  Select_Female_TorsoBack_Left_Medial_LowerBack: "왼쪽 안쪽 허리(내측 하부)",
  Select_Female_TorsoBack_Right_ShoulderBlade: "오른쪽 견갑골",
  Select_Female_TorsoBack_Left_ShoulderBlade: "왼쪽 견갑골",
  Select_Female_TorsoBack_Right_Medial_MidBack: "오른쪽 안쪽 등 중부",
  Select_Female_TorsoBack_Left_Medial_MidBack: "왼쪽 안쪽 등 중부",
  Select_Female_TorsoBack_Right_Trapezeum: "오른쪽 승모근",
  Select_Female_TorsoBack_Left_Trapezeum: "왼쪽 승모근",
  // Female torso — front
  Select_Female_TorsoFront_Left_LowerChest: "왼쪽 아래 가슴",
  Select_Female_TorsoFront_Right_LowerChest: "오른쪽 아래 가슴",
  Select_Female_TorsoFront_Left_UpperChest: "왼쪽 윗가슴",
  Select_Female_TorsoFront_Right_UpperChest: "오른쪽 윗가슴",
  Select_Female_TorsoFront_Right_RibCage: "오른쪽 갈비뼈 부위",
  Select_Female_TorsoFront_Left_RibCage: "왼쪽 갈비뼈 부위",
  Select_Female_TorsoFront_Epigastrium: "명치(상복부 중앙)",
  Select_Female_TorsoFront_Umbellical: "배꼽 부위",
  Select_Female_TorsoFront_Lower_MiddleQuadrant: "아랫배 중앙",
  Select_Female_TorsoFront_Left_UpperQuadrant: "왼쪽 윗배",
  Select_Female_TorsoFront_Left_UpperQuadrant_2: "왼쪽 윗배(2)",
  Select_Female_TorsoFront_Left_Flank: "왼쪽 옆구리",
  Select_Female_TorsoFront_Left_Flank_2: "왼쪽 옆구리(2)",
  Select_Female_TorsoFront_Left_LowerQuadrant: "왼쪽 아랫배",
  Select_Female_TorsoFront_Right_LowerQuadrant: "오른쪽 아랫배",
  Select_Female_TorsoFront_Middle_Chest: "가슴 중앙",

  // Male legs — back
  Select_MaleLegs_Back_Right_LowerCalf: "오른쪽 아래 종아리",
  Select_MaleLegs_Back_Left_LowerCalf: "왼쪽 아래 종아리",
  Select_MaleLegs_Back_Right_Calf: "오른쪽 종아리",
  Select_MaleLegs_Back_Left_Calf: "왼쪽 종아리",
  Select_MaleLegs_Back_Right_BackofKnee: "오른쪽 오금(무릎 뒤)",
  Select_MaleLegs_Back_Left_BackofKnee: "왼쪽 오금(무릎 뒤)",
  Select_MaleLegs_Back_Right_HamString: "오른쪽 햄스트링",
  Select_MaleLegs_Back_Left_HamString: "왼쪽 햄스트링",
  // Male legs — front
  Select_MaleLegs_Front_LeftFoot: "왼쪽 발",
  Select_MaleLegs_Front_RightFoot: "오른쪽 발",
  Select_MaleLegs_Front_LeftAnkle: "왼쪽 발목",
  Select_MaleLegs_Front_RightAnkle: "오른쪽 발목",
  Select_MaleLegs_Front_LeftShin: "왼쪽 정강이",
  Select_MaleLegs_Front_RightShin: "오른쪽 정강이",
  Select_MaleLegs_Front_LeftKnee: "왼쪽 무릎",
  Select_MaleLegs_Front_RightKnee: "오른쪽 무릎",
  Select_MaleLegs_Front_Left_InnerThigh: "왼쪽 안쪽 허벅지",
  Select_MaleLegs_Front_Right_InnerThigh: "오른쪽 안쪽 허벅지",
  Select_MaleLegs_Front_Left_OuterThigh: "왼쪽 바깥 허벅지",
  Select_MaleLegs_Front_Right_OuterThigh: "오른쪽 바깥 허벅지",

  // Male torso — back
  Select_Right_Lateral_LowerBack: "오른쪽 옆 허리(외측 하부)",
  Select_Left_Lateral_LowerBack: "왼쪽 옆 허리(외측 하부)",
  Select_Right_Lats: "오른쪽 광배근",
  Select_Left_Lats: "왼쪽 광배근",
  Select_Right_Medial_LowerBack: "오른쪽 안쪽 허리(내측 하부)",
  Select_Left_Medial_LowerBack: "왼쪽 안쪽 허리(내측 하부)",
  Select_Right_ShoulderBlade: "오른쪽 견갑골",
  Select_Left_ShoulderBlade: "왼쪽 견갑골",
  Select_Right_Medial_MidBack: "오른쪽 안쪽 등 중부",
  Select_Left_Medial_MidBack: "왼쪽 안쪽 등 중부",
  Select_Right_Trapezeum: "오른쪽 승모근",
  Select_Left_Trapezeum: "왼쪽 승모근",
  // Male torso — front
  Select_Lower_MiddleQuadrant: "아랫배 중앙",
  Select_Left_LowerQuadrant: "왼쪽 아랫배",
  Select_Right_LowerQuadrant: "오른쪽 아랫배",
  Select_Left_Chest: "왼쪽 가슴",
  Select_Right_Chest: "오른쪽 가슴",
  Select_Left_RibCage: "왼쪽 갈비뼈 부위",
  Select_Right_RibCage: "오른쪽 갈비뼈 부위",
  Select_Epigastrium: "명치(상복부 중앙)",
  Select_Umbellical: "배꼽 부위",
  Select_Left_UpperQuadrant: "왼쪽 윗배",
  Select_Right_UpperQuadrant: "오른쪽 윗배",
  Select_Left_Flank: "왼쪽 옆구리",
  Select_Right_Flank: "오른쪽 옆구리",
  Select_MiddleChest: "가슴 중앙",
};
