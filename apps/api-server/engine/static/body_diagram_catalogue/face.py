"""Face diagram — unisex.

Select_LeftSide / Select_RightSide use body_part="cheek" (UNCERTAIN — region_id
only says "side of face"; could be cheek, temple, or general lateral face.
Confirm with design/clinical before treating as settled vocab).
"""
from __future__ import annotations

from engine.static.body_diagram_catalogue.types import PrefillMapping, RegionCoding

PREFILL_MAPPINGS: list[PrefillMapping] = [
    PrefillMapping(
        body_part="neck", side="midline", surface="front", sex_variant=None,
        diagram_file="Face 1.svg", region_id="Select_Neck",
    ),
    PrefillMapping(
        body_part="ear", side="left", surface="front", sex_variant=None,
        diagram_file="Face 1.svg", region_id="Select_LeftEar",
    ),
    PrefillMapping(
        body_part="ear", side="right", surface="front", sex_variant=None,
        diagram_file="Face 1.svg", region_id="Select_RightEar",
    ),
    PrefillMapping(
        body_part="mouth", side="midline", surface="front", sex_variant=None,
        diagram_file="Face 1.svg", region_id="Select_Mouth",
    ),
    PrefillMapping(
        body_part="nose", side="midline", surface="front", sex_variant=None,
        diagram_file="Face 1.svg", region_id="Select_Nose",
    ),
    PrefillMapping(
        body_part="eye", side="left", surface="front", sex_variant=None,
        diagram_file="Face 1.svg", region_id="Select_LeftEye",
    ),
    PrefillMapping(
        body_part="eye", side="right", surface="front", sex_variant=None,
        diagram_file="Face 1.svg", region_id="Select_RightEye",
    ),
    PrefillMapping(
        body_part="chin", side="midline", surface="front", sex_variant=None,
        diagram_file="Face 1.svg", region_id="Select_Chin",
    ),
    PrefillMapping(
        body_part="forehead", side="midline", surface="front", sex_variant=None,
        diagram_file="Face 1.svg", region_id="Select_Forehead",
    ),
    # UNCERTAIN body_part — see module docstring ("cheek" pending clinical confirm)
    PrefillMapping(
        body_part="cheek", side="left", surface="front", sex_variant=None,
        diagram_file="Face 1.svg", region_id="Select_LeftSide",
    ),
    PrefillMapping(
        body_part="cheek", side="right", surface="front", sex_variant=None,
        diagram_file="Face 1.svg", region_id="Select_RightSide",
    ),
]

REGION_CODINGS: list[RegionCoding] = [
    RegionCoding(
        region_id="Select_Neck",
        layman_term="neck",
        anatomical_term="cervical region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="midline",
    ),
    RegionCoding(
        region_id="Select_LeftEar",
        layman_term="left ear",
        anatomical_term="left ear region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="left",
    ),
    RegionCoding(
        region_id="Select_RightEar",
        layman_term="right ear",
        anatomical_term="right ear region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="right",
    ),
    RegionCoding(
        region_id="Select_Chin",
        layman_term="chin",
        anatomical_term="chin region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="midline",
    ),
    RegionCoding(
        region_id="Select_Mouth",
        layman_term="mouth",
        anatomical_term="oral region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="midline",
    ),
    RegionCoding(
        region_id="Select_Nose",
        layman_term="nose",
        anatomical_term="nasal region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="midline",
    ),
    RegionCoding(
        region_id="Select_LeftEye",
        layman_term="left eye",
        anatomical_term="left ocular region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="left",
    ),
    RegionCoding(
        region_id="Select_RightEye",
        layman_term="right eye",
        anatomical_term="right ocular region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="right",
    ),
    RegionCoding(
        region_id="Select_LeftSide",
        layman_term="left side of face",
        anatomical_term="left facial region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="left",
    ),
    RegionCoding(
        region_id="Select_RightSide",
        layman_term="right side of face",
        anatomical_term="right facial region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="right",
    ),
    RegionCoding(
        region_id="Select_Forehead",
        layman_term="forehead",
        anatomical_term="frontal region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="midline",
    ),
]
