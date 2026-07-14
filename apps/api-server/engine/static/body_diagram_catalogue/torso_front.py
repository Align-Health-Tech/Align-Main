"""Front torso diagrams — sex-split.

Left_UpperQuadrant vs Left_UpperQuadrant_2 share body_part/side/surface
(upper_abdomen/left/front) — only the first PrefillMapping wins for LLM
suggestion; the other remains tap-only.
"""
from __future__ import annotations

from engine.static.body_diagram_catalogue.types import PrefillMapping, RegionCoding

PREFILL_MAPPINGS: list[PrefillMapping] = [
    PrefillMapping(
        body_part="chest", side="left", surface="front", sex_variant="female",
        diagram_file="Female Torso Front 1.svg", region_id="Select_Female_TorsoFront_Left_LowerChest",
    ),
    PrefillMapping(
        body_part="chest", side="right", surface="front", sex_variant="female",
        diagram_file="Female Torso Front 1.svg", region_id="Select_Female_TorsoFront_Right_LowerChest",
    ),
    PrefillMapping(
        body_part="chest", side="left", surface="front", sex_variant="female",
        diagram_file="Female Torso Front 1.svg", region_id="Select_Female_TorsoFront_Left_UpperChest",
    ),
    PrefillMapping(
        body_part="chest", side="right", surface="front", sex_variant="female",
        diagram_file="Female Torso Front 1.svg", region_id="Select_Female_TorsoFront_Right_UpperChest",
    ),
    PrefillMapping(
        body_part="rib_cage", side="right", surface="front", sex_variant="female",
        diagram_file="Female Torso Front 1.svg", region_id="Select_Female_TorsoFront_Right_RibCage",
    ),
    PrefillMapping(
        body_part="rib_cage", side="left", surface="front", sex_variant="female",
        diagram_file="Female Torso Front 1.svg", region_id="Select_Female_TorsoFront_Left_RibCage",
    ),
    PrefillMapping(
        body_part="epigastrium", side="midline", surface="front", sex_variant="female",
        diagram_file="Female Torso Front 1.svg", region_id="Select_Female_TorsoFront_Epigastrium",
    ),
    PrefillMapping(
        body_part="umbilical", side="midline", surface="front", sex_variant="female",
        diagram_file="Female Torso Front 1.svg", region_id="Select_Female_TorsoFront_Umbellical",
    ),
    PrefillMapping(
        body_part="lower_abdomen", side="midline", surface="front", sex_variant="female",
        diagram_file="Female Torso Front 1.svg", region_id="Select_Female_TorsoFront_Lower_MiddleQuadrant",
    ),
    PrefillMapping(
        body_part="upper_abdomen", side="left", surface="front", sex_variant="female",
        diagram_file="Female Torso Front 1.svg",
        region_id="Select_Female_TorsoFront_Left_UpperQuadrant",
    ),
    PrefillMapping(
        body_part="upper_abdomen", side="left", surface="front", sex_variant="female",
        diagram_file="Female Torso Front 1.svg",
        region_id="Select_Female_TorsoFront_Left_UpperQuadrant_2",
    ),
    PrefillMapping(
        body_part="flank", side="left", surface="front", sex_variant="female",
        diagram_file="Female Torso Front 1.svg", region_id="Select_Female_TorsoFront_Left_Flank",
    ),
    PrefillMapping(
        body_part="flank", side="left", surface="front", sex_variant="female",
        diagram_file="Female Torso Front 1.svg", region_id="Select_Female_TorsoFront_Left_Flank_2",
    ),
    PrefillMapping(
        body_part="lower_abdomen", side="left", surface="front", sex_variant="female",
        diagram_file="Female Torso Front 1.svg", region_id="Select_Female_TorsoFront_Left_LowerQuadrant",
    ),
    PrefillMapping(
        body_part="lower_abdomen", side="right", surface="front", sex_variant="female",
        diagram_file="Female Torso Front 1.svg", region_id="Select_Female_TorsoFront_Right_LowerQuadrant",
    ),
    PrefillMapping(
        body_part="chest", side="midline", surface="front", sex_variant="female",
        diagram_file="Female Torso Front 1.svg", region_id="Select_Female_TorsoFront_Middle_Chest",
    ),
    PrefillMapping(
        body_part="lower_abdomen", side="midline", surface="front", sex_variant="male",
        diagram_file="Torso Front Male (SVG Labelled).svg", region_id="Select_Lower_MiddleQuadrant",
    ),
    PrefillMapping(
        body_part="lower_abdomen", side="left", surface="front", sex_variant="male",
        diagram_file="Torso Front Male (SVG Labelled).svg", region_id="Select_Left_LowerQuadrant",
    ),
    PrefillMapping(
        body_part="lower_abdomen", side="right", surface="front", sex_variant="male",
        diagram_file="Torso Front Male (SVG Labelled).svg", region_id="Select_Right_LowerQuadrant",
    ),
    PrefillMapping(
        body_part="chest", side="left", surface="front", sex_variant="male",
        diagram_file="Torso Front Male (SVG Labelled).svg", region_id="Select_Left_Chest",
    ),
    PrefillMapping(
        body_part="chest", side="right", surface="front", sex_variant="male",
        diagram_file="Torso Front Male (SVG Labelled).svg", region_id="Select_Right_Chest",
    ),
    PrefillMapping(
        body_part="rib_cage", side="left", surface="front", sex_variant="male",
        diagram_file="Torso Front Male (SVG Labelled).svg", region_id="Select_Left_RibCage",
    ),
    PrefillMapping(
        body_part="rib_cage", side="right", surface="front", sex_variant="male",
        diagram_file="Torso Front Male (SVG Labelled).svg", region_id="Select_Right_RibCage",
    ),
    PrefillMapping(
        body_part="epigastrium", side="midline", surface="front", sex_variant="male",
        diagram_file="Torso Front Male (SVG Labelled).svg", region_id="Select_Epigastrium",
    ),
    PrefillMapping(
        body_part="umbilical", side="midline", surface="front", sex_variant="male",
        diagram_file="Torso Front Male (SVG Labelled).svg", region_id="Select_Umbellical",
    ),
    PrefillMapping(
        body_part="upper_abdomen", side="left", surface="front", sex_variant="male",
        diagram_file="Torso Front Male (SVG Labelled).svg", region_id="Select_Left_UpperQuadrant",
    ),
    PrefillMapping(
        body_part="upper_abdomen", side="right", surface="front", sex_variant="male",
        diagram_file="Torso Front Male (SVG Labelled).svg", region_id="Select_Right_UpperQuadrant",
    ),
    PrefillMapping(
        body_part="flank", side="left", surface="front", sex_variant="male",
        diagram_file="Torso Front Male (SVG Labelled).svg", region_id="Select_Left_Flank",
    ),
    PrefillMapping(
        body_part="flank", side="right", surface="front", sex_variant="male",
        diagram_file="Torso Front Male (SVG Labelled).svg", region_id="Select_Right_Flank",
    ),
    PrefillMapping(
        body_part="chest", side="midline", surface="front", sex_variant="male",
        diagram_file="Torso Front Male (SVG Labelled).svg", region_id="Select_MiddleChest",
    ),
]

REGION_CODINGS: list[RegionCoding] = [
    RegionCoding(
        region_id="Select_Female_TorsoFront_Left_LowerChest",
        layman_term="left lower chest",
        anatomical_term="left lower anterior thorax",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="left",
    ),
    RegionCoding(
        region_id="Select_Female_TorsoFront_Right_LowerChest",
        layman_term="right lower chest",
        anatomical_term="right lower anterior thorax",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="right",
    ),
    RegionCoding(
        region_id="Select_Female_TorsoFront_Left_UpperChest",
        layman_term="left upper chest",
        anatomical_term="left upper anterior thorax",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="left",
    ),
    RegionCoding(
        region_id="Select_Female_TorsoFront_Right_UpperChest",
        layman_term="right upper chest",
        anatomical_term="right upper anterior thorax",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="right",
    ),
    RegionCoding(
        region_id="Select_Female_TorsoFront_Right_RibCage",
        layman_term="right rib cage",
        anatomical_term="right costal region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="right",
    ),
    RegionCoding(
        region_id="Select_Female_TorsoFront_Left_RibCage",
        layman_term="left rib cage",
        anatomical_term="left costal region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="left",
    ),
    RegionCoding(
        region_id="Select_Female_TorsoFront_Epigastrium",
        layman_term="epigastrium",
        anatomical_term="epigastric region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="midline",
    ),
    RegionCoding(
        region_id="Select_Female_TorsoFront_Umbellical",
        layman_term="umbilical area",
        anatomical_term="umbilical region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="midline",
    ),
    RegionCoding(
        region_id="Select_Female_TorsoFront_Lower_MiddleQuadrant",
        layman_term="lower middle abdomen",
        anatomical_term="hypogastric region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="midline",
    ),
    RegionCoding(
        region_id="Select_Female_TorsoFront_Left_UpperQuadrant",
        layman_term="left upper abdomen (medial)",
        anatomical_term="left upper abdominal quadrant (medial)",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="left",
    ),
    RegionCoding(
        region_id="Select_Female_TorsoFront_Left_UpperQuadrant_2",
        layman_term="left upper abdomen (lateral)",
        anatomical_term="left upper abdominal quadrant (lateral)",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="left",
    ),
    RegionCoding(
        region_id="Select_Female_TorsoFront_Left_Flank",
        layman_term="left flank (medial)",
        anatomical_term="left flank region (medial)",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="left",
    ),
    RegionCoding(
        region_id="Select_Female_TorsoFront_Left_Flank_2",
        layman_term="left flank (lateral)",
        anatomical_term="left flank region (lateral)",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="left",
    ),
    RegionCoding(
        region_id="Select_Female_TorsoFront_Left_LowerQuadrant",
        layman_term="left lower abdomen",
        anatomical_term="left lower abdominal quadrant",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="left",
    ),
    RegionCoding(
        region_id="Select_Female_TorsoFront_Right_LowerQuadrant",
        layman_term="right lower abdomen",
        anatomical_term="right lower abdominal quadrant",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="right",
    ),
    RegionCoding(
        region_id="Select_Female_TorsoFront_Middle_Chest",
        layman_term="middle chest",
        anatomical_term="midline anterior thorax",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="midline",
    ),
    RegionCoding(
        region_id="Select_Lower_MiddleQuadrant",
        layman_term="lower middle abdomen",
        anatomical_term="hypogastric region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="midline",
    ),
    RegionCoding(
        region_id="Select_Left_LowerQuadrant",
        layman_term="left lower abdomen",
        anatomical_term="left lower abdominal quadrant",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="left",
    ),
    RegionCoding(
        region_id="Select_Right_LowerQuadrant",
        layman_term="right lower abdomen",
        anatomical_term="right lower abdominal quadrant",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="right",
    ),
    RegionCoding(
        region_id="Select_Left_Chest",
        layman_term="left chest",
        anatomical_term="left anterior thorax",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="left",
    ),
    RegionCoding(
        region_id="Select_Right_Chest",
        layman_term="right chest",
        anatomical_term="right anterior thorax",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="right",
    ),
    RegionCoding(
        region_id="Select_Left_RibCage",
        layman_term="left rib cage",
        anatomical_term="left costal region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="left",
    ),
    RegionCoding(
        region_id="Select_Right_RibCage",
        layman_term="right rib cage",
        anatomical_term="right costal region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="right",
    ),
    RegionCoding(
        region_id="Select_Epigastrium",
        layman_term="epigastrium",
        anatomical_term="epigastric region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="midline",
    ),
    RegionCoding(
        region_id="Select_Umbellical",
        layman_term="umbilical area",
        anatomical_term="umbilical region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="midline",
    ),
    RegionCoding(
        region_id="Select_Left_UpperQuadrant",
        layman_term="left upper abdomen",
        anatomical_term="left upper abdominal quadrant",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="left",
    ),
    RegionCoding(
        region_id="Select_Right_UpperQuadrant",
        layman_term="right upper abdomen",
        anatomical_term="right upper abdominal quadrant",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="right",
    ),
    RegionCoding(
        region_id="Select_Left_Flank",
        layman_term="left flank",
        anatomical_term="left flank region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="left",
    ),
    RegionCoding(
        region_id="Select_Right_Flank",
        layman_term="right flank",
        anatomical_term="right flank region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="right",
    ),
    RegionCoding(
        region_id="Select_MiddleChest",
        layman_term="middle chest",
        anatomical_term="midline anterior thorax",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="midline",
    ),
]
