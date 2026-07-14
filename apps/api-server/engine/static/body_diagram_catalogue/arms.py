"""Arm diagrams — unisex front/back left/right."""
from __future__ import annotations

from engine.static.body_diagram_catalogue.types import PrefillMapping, RegionCoding

PREFILL_MAPPINGS: list[PrefillMapping] = [
    PrefillMapping(
        body_part="hand", side="left", surface="back", sex_variant=None,
        diagram_file="Arm Left Back.svg", region_id="Select_LeftHand",
    ),
    PrefillMapping(
        body_part="wrist", side="left", surface="back", sex_variant=None,
        diagram_file="Arm Left Back.svg", region_id="Select_LeftWrist",
    ),
    PrefillMapping(
        body_part="forearm", side="left", surface="back", sex_variant=None,
        diagram_file="Arm Left Back.svg", region_id="Select_LeftForearm",
    ),
    PrefillMapping(
        body_part="tricep", side="left", surface="back", sex_variant=None,
        diagram_file="Arm Left Back.svg", region_id="Select_LeftTricep",
    ),
    PrefillMapping(
        body_part="shoulder", side="left", surface="back", sex_variant=None,
        diagram_file="Arm Left Back.svg", region_id="Select_LeftShoulder",
    ),
    PrefillMapping(
        body_part="wrist", side="left", surface="front", sex_variant=None,
        diagram_file="Arm Left Front.svg", region_id="Select_LeftWrist",
    ),
    PrefillMapping(
        body_part="hand", side="left", surface="front", sex_variant=None,
        diagram_file="Arm Left Front.svg", region_id="Select_LeftHand",
    ),
    PrefillMapping(
        body_part="forearm", side="left", surface="front", sex_variant=None,
        diagram_file="Arm Left Front.svg", region_id="Select_LeftForearm",
    ),
    PrefillMapping(
        body_part="bicep", side="left", surface="front", sex_variant=None,
        diagram_file="Arm Left Front.svg", region_id="Select_LeftBicep",
    ),
    PrefillMapping(
        body_part="shoulder", side="left", surface="front", sex_variant=None,
        diagram_file="Arm Left Front.svg", region_id="Select_LeftShoulder",
    ),
    PrefillMapping(
        body_part="hand", side="right", surface="back", sex_variant=None,
        diagram_file="Arm Right Back.svg", region_id="Select_RightHand",
    ),
    PrefillMapping(
        body_part="wrist", side="right", surface="back", sex_variant=None,
        diagram_file="Arm Right Back.svg", region_id="Select_RightWrist",
    ),
    PrefillMapping(
        body_part="forearm", side="right", surface="back", sex_variant=None,
        diagram_file="Arm Right Back.svg", region_id="Select_RightForearm",
    ),
    PrefillMapping(
        body_part="tricep", side="right", surface="back", sex_variant=None,
        diagram_file="Arm Right Back.svg", region_id="Select_RightTricep",
    ),
    PrefillMapping(
        body_part="shoulder", side="right", surface="back", sex_variant=None,
        diagram_file="Arm Right Back.svg", region_id="Select_RightShoulder",
    ),
    PrefillMapping(
        body_part="wrist", side="right", surface="front", sex_variant=None,
        diagram_file="Arm Right Front.svg", region_id="Select_RightWrist",
    ),
    PrefillMapping(
        body_part="hand", side="right", surface="front", sex_variant=None,
        diagram_file="Arm Right Front.svg", region_id="Select_RightHand",
    ),
    PrefillMapping(
        body_part="forearm", side="right", surface="front", sex_variant=None,
        diagram_file="Arm Right Front.svg", region_id="Select_RightForearm",
    ),
    PrefillMapping(
        body_part="bicep", side="right", surface="front", sex_variant=None,
        diagram_file="Arm Right Front.svg", region_id="Select_RightBicep",
    ),
    PrefillMapping(
        body_part="shoulder", side="right", surface="front", sex_variant=None,
        diagram_file="Arm Right Front.svg", region_id="Select_RightShoulder",
    ),
]

REGION_CODINGS: list[RegionCoding] = [
    RegionCoding(
        region_id="Select_LeftHand",
        layman_term="left hand",
        anatomical_term="left hand region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="left",
    ),
    RegionCoding(
        region_id="Select_LeftWrist",
        layman_term="left wrist",
        anatomical_term="left carpal region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="left",
    ),
    RegionCoding(
        region_id="Select_LeftForearm",
        layman_term="left forearm",
        anatomical_term="left forearm region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="left",
    ),
    RegionCoding(
        region_id="Select_LeftShoulder",
        layman_term="left shoulder",
        anatomical_term="left shoulder region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="left",
    ),
    RegionCoding(
        region_id="Select_LeftTricep",
        layman_term="back of left upper arm",
        anatomical_term="left triceps region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="left",
    ),
    RegionCoding(
        region_id="Select_LeftBicep",
        layman_term="front of left upper arm",
        anatomical_term="left biceps region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="left",
    ),
    RegionCoding(
        region_id="Select_RightHand",
        layman_term="right hand",
        anatomical_term="right hand region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="right",
    ),
    RegionCoding(
        region_id="Select_RightWrist",
        layman_term="right wrist",
        anatomical_term="right carpal region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="right",
    ),
    RegionCoding(
        region_id="Select_RightForearm",
        layman_term="right forearm",
        anatomical_term="right forearm region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="right",
    ),
    RegionCoding(
        region_id="Select_RightShoulder",
        layman_term="right shoulder",
        anatomical_term="right shoulder region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="right",
    ),
    RegionCoding(
        region_id="Select_RightTricep",
        layman_term="back of right upper arm",
        anatomical_term="right triceps region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="right",
    ),
    RegionCoding(
        region_id="Select_RightBicep",
        layman_term="front of right upper arm",
        anatomical_term="right biceps region",
        fhir_system="http://snomed.info/sct",
        fhir_code="TODO-SNOMED-LOOKUP",
        side="right",
    ),
]
