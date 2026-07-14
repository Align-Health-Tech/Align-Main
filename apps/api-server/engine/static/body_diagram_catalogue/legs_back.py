"""Back leg diagrams — sex-split. Hamstring maps to body_part=thigh, surface=back."""
from __future__ import annotations

from engine.static.body_diagram_catalogue.types import PrefillMapping, RegionCoding

PREFILL_MAPPINGS: list[PrefillMapping] = [
    PrefillMapping(
        body_part="lower_calf", side="right", surface="back", sex_variant="female",
        diagram_file="Female Legs Back 1.svg", region_id="Select_FemaleLegs_Back_Right_LowerCalf",
    ),
    PrefillMapping(
        body_part="lower_calf", side="left", surface="back", sex_variant="female",
        diagram_file="Female Legs Back 1.svg", region_id="Select_FemaleLegs_Back_Left_LowerCalf",
    ),
    PrefillMapping(
        body_part="calf", side="right", surface="back", sex_variant="female",
        diagram_file="Female Legs Back 1.svg", region_id="Select_FemaleLegs_Back_Right_Calf",
    ),
    PrefillMapping(
        body_part="calf", side="left", surface="back", sex_variant="female",
        diagram_file="Female Legs Back 1.svg", region_id="Select_FemaleLegs_Back_Left_Calf",
    ),
    PrefillMapping(
        body_part="back_of_knee", side="right", surface="back", sex_variant="female",
        diagram_file="Female Legs Back 1.svg", region_id="Select_FemaleLegs_Back_Right_BackofKnee",
    ),
    PrefillMapping(
        body_part="back_of_knee", side="left", surface="back", sex_variant="female",
        diagram_file="Female Legs Back 1.svg", region_id="Select_FemaleLegs_Back_Left_BackofKnee",
    ),
    PrefillMapping(
        body_part="thigh", side="right", surface="back", sex_variant="female",
        diagram_file="Female Legs Back 1.svg", region_id="Select_FemaleLegs_Back_Right_Hamstring",
    ),
    PrefillMapping(
        body_part="thigh", side="left", surface="back", sex_variant="female",
        diagram_file="Female Legs Back 1.svg", region_id="Select_FemaleLegs_Back_Left_Hamstring",
    ),
    PrefillMapping(
        body_part="lower_calf", side="right", surface="back", sex_variant="male",
        diagram_file="Male Legs Back 1.svg", region_id="Select_MaleLegs_Back_Right_LowerCalf",
    ),
    PrefillMapping(
        body_part="lower_calf", side="left", surface="back", sex_variant="male",
        diagram_file="Male Legs Back 1.svg", region_id="Select_MaleLegs_Back_Left_LowerCalf",
    ),
    PrefillMapping(
        body_part="calf", side="right", surface="back", sex_variant="male",
        diagram_file="Male Legs Back 1.svg", region_id="Select_MaleLegs_Back_Right_Calf",
    ),
    PrefillMapping(
        body_part="calf", side="left", surface="back", sex_variant="male",
        diagram_file="Male Legs Back 1.svg", region_id="Select_MaleLegs_Back_Left_Calf",
    ),
    PrefillMapping(
        body_part="back_of_knee", side="right", surface="back", sex_variant="male",
        diagram_file="Male Legs Back 1.svg", region_id="Select_MaleLegs_Back_Right_BackofKnee",
    ),
    PrefillMapping(
        body_part="back_of_knee", side="left", surface="back", sex_variant="male",
        diagram_file="Male Legs Back 1.svg", region_id="Select_MaleLegs_Back_Left_BackofKnee",
    ),
    PrefillMapping(
        body_part="thigh", side="right", surface="back", sex_variant="male",
        diagram_file="Male Legs Back 1.svg", region_id="Select_MaleLegs_Back_Right_HamString",
    ),
    PrefillMapping(
        body_part="thigh", side="left", surface="back", sex_variant="male",
        diagram_file="Male Legs Back 1.svg", region_id="Select_MaleLegs_Back_Left_HamString",
    ),
]

REGION_CODINGS: list[RegionCoding] = [
    RegionCoding(
        region_id="Select_FemaleLegs_Back_Right_LowerCalf",
        layman_term="right lower calf",
        anatomical_term="right distal posterior leg region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="right",
    ),
    RegionCoding(
        region_id="Select_FemaleLegs_Back_Left_LowerCalf",
        layman_term="left lower calf",
        anatomical_term="left distal posterior leg region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="left",
    ),
    RegionCoding(
        region_id="Select_FemaleLegs_Back_Right_Calf",
        layman_term="right calf",
        anatomical_term="right calf region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="right",
    ),
    RegionCoding(
        region_id="Select_FemaleLegs_Back_Left_Calf",
        layman_term="left calf",
        anatomical_term="left calf region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="left",
    ),
    RegionCoding(
        region_id="Select_FemaleLegs_Back_Right_BackofKnee",
        layman_term="back of right knee",
        anatomical_term="right popliteal region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="right",
    ),
    RegionCoding(
        region_id="Select_FemaleLegs_Back_Left_BackofKnee",
        layman_term="back of left knee",
        anatomical_term="left popliteal region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="left",
    ),
    RegionCoding(
        region_id="Select_FemaleLegs_Back_Right_Hamstring",
        layman_term="right hamstring",
        anatomical_term="right posterior thigh region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="right",
    ),
    RegionCoding(
        region_id="Select_FemaleLegs_Back_Left_Hamstring",
        layman_term="left hamstring",
        anatomical_term="left posterior thigh region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="left",
    ),
    RegionCoding(
        region_id="Select_MaleLegs_Back_Right_LowerCalf",
        layman_term="right lower calf",
        anatomical_term="right distal posterior leg region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="right",
    ),
    RegionCoding(
        region_id="Select_MaleLegs_Back_Left_LowerCalf",
        layman_term="left lower calf",
        anatomical_term="left distal posterior leg region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="left",
    ),
    RegionCoding(
        region_id="Select_MaleLegs_Back_Right_Calf",
        layman_term="right calf",
        anatomical_term="right calf region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="right",
    ),
    RegionCoding(
        region_id="Select_MaleLegs_Back_Left_Calf",
        layman_term="left calf",
        anatomical_term="left calf region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="left",
    ),
    RegionCoding(
        region_id="Select_MaleLegs_Back_Right_BackofKnee",
        layman_term="back of right knee",
        anatomical_term="right popliteal region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="right",
    ),
    RegionCoding(
        region_id="Select_MaleLegs_Back_Left_BackofKnee",
        layman_term="back of left knee",
        anatomical_term="left popliteal region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="left",
    ),
    RegionCoding(
        region_id="Select_MaleLegs_Back_Right_HamString",
        layman_term="right hamstring",
        anatomical_term="right posterior thigh region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="right",
    ),
    RegionCoding(
        region_id="Select_MaleLegs_Back_Left_HamString",
        layman_term="left hamstring",
        anatomical_term="left posterior thigh region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="left",
    ),
]
