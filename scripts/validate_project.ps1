[CmdletBinding()]
param(
    [string]$PythonPath
)

$ErrorActionPreference = 'Stop'
$required = @(
    'README.md',
    'CONTRIBUTING.md',
    'SECURITY.md',
    'CITATION.cff',
    'pyproject.toml',
    '.github/ISSUE_TEMPLATE/bug_report.yml',
    '.github/ISSUE_TEMPLATE/research_methodology.yml',
    '.github/ISSUE_TEMPLATE/reproducibility.yml',
    '.github/ISSUE_TEMPLATE/documentation.yml',
    'configs/e001.example.toml',
    'configs/e001-phase-2d-a-preregistered.json',
    'configs/e001-phase-2d-b-final-protocol.json',
    'configs/e001-phase-2e-a-robustness-protocol.json',
    'configs/e001-phase-2f-a-inference-protocol.json',
    'outputs/deep_learning/e001_cnn_protocol.json',
    'data/README.md',
    'data/manifests/example-dataset.toml',
    'data/manifests/e001-ea-lidar-dtm.toml',
    'docs/environment-audit.md',
    'docs/e001-feasibility-audit.md',
    'docs/e001-phase-2a5-curation-gate.md',
    'docs/e001-phase-2b-terrain.md',
    'docs/e001-phase-2b5-full-terrain.md',
    'docs/e001-phase-2c-background-and-splits.md',
    'docs/e001-phase-2d-a-preregistration.md',
    'docs/e001-phase-2d-a-development-selection.md',
    'docs/e001-phase-2d-b-final-protocol.md',
    'docs/e001-phase-2d-baseline-modelling.md',
    'docs/e001-phase-2e-a-robustness-protocol.md',
    'docs/e001-phase-2e-robustness.md',
    'docs/e001-phase-2eb-compact-cnn.md',
    'docs/e001-phase-2f-a-controlled-inference.md',
    'docs/e001-phase-2f-b-controlled-inference.md',
    'docs/research-charter.md',
    'docs/literature-novelty-audit.md',
    'docs/licensing-and-attribution.md',
    'docs/dataset-decision-record.md',
    'docs/research-questions.md',
    'docs/roadmap.md',
    'docs/decision-log.md',
    'docs/project-quality-bar.md',
    'docs/claims-register.md',
    'research-log/README.md',
    'research-log/2026-08-28-phase-2b.md',
    'research-log/2026-08-29-phase-2b5.md',
    'research-log/2026-08-29-phase-2c.md',
    'research-log/2026-08-29-phase-2d-a.md',
    'research-log/2026-08-29-phase-2d-b.md',
    'research-log/2026-08-29-phase-2e-a.md',
    'research-log/2026-08-29-phase-2eb0.md',
    'research-log/2026-08-29-phase-2eb.md',
    'research-log/2026-08-29-phase-2f-a.md',
    'research-log/2026-08-30-phase-2f-b.md',
    'experiments/E001_geographic_baseline.md',
    'scripts/doctor.ps1',
    'scripts/audit_nhle_bowl_barrows.py',
    'scripts/curate_e001_labels.py',
    'scripts/reconstruct_e001_sites.py',
    'scripts/acquire_e001_terrain_pilot.py',
    'scripts/acquire_e001_full_terrain.py',
    'scripts/audit_e001_full_terrain.py',
    'scripts/build_e001_backgrounds.py',
    'scripts/audit_e001_background_pilot.py',
    'scripts/freeze_e001_splits.py',
    'scripts/audit_e001_dataset.py',
    'scripts/run_e001_development_baselines.py',
    'scripts/run_e001_final_evaluation.py',
    'scripts/render_e001_final_figures.py',
    'scripts/freeze_e001_robustness_folds.py',
    'scripts/run_e001_robustness.py',
    'scripts/render_e001_robustness_figures.py',
    'scripts/freeze_e001_cnn_protocol.py',
    'scripts/run_e001_cnn_geographic_cv.py',
    'scripts/render_e001_cnn_figures.py',
    'scripts/freeze_e001_inference_protocol.py',
    'scripts/smoke_e001_inference.py',
    'scripts/run_e001_private_inference.py',
    'scripts/estimate_e001_terrain_acquisition.py',
    'src/archaeoai/__init__.py',
    'src/archaeoai/config.py',
    'src/archaeoai/paths.py',
    'src/archaeoai/nhle_audit.py',
    'src/archaeoai/curation.py',
    'src/archaeoai/terrain_metadata.py',
    'src/archaeoai/terrain/acquisition.py',
    'src/archaeoai/terrain/audit.py',
    'src/archaeoai/terrain/background.py',
    'src/archaeoai/terrain/index.py',
    'src/archaeoai/terrain/patches.py',
    'src/archaeoai/terrain/privacy.py',
    'src/archaeoai/terrain/qa.py',
    'src/archaeoai/terrain/raster.py',
    'src/archaeoai/terrain/representations.py',
    'src/archaeoai/terrain/full_dataset.py',
    'src/archaeoai/terrain/validation.py',
    'src/archaeoai/dataset.py',
    'src/archaeoai/splits.py',
    'src/archaeoai/model_data.py',
    'src/archaeoai/modelling.py',
    'src/archaeoai/final_evaluation.py',
    'src/archaeoai/robustness.py',
    'src/archaeoai/deep_learning.py',
    'src/archaeoai/cnn_training.py',
    'src/archaeoai/inference.py',
    'src/archaeoai/data/manifest.py',
    'tests/test_config.py',
    'tests/test_manifest.py',
    'tests/test_package.py',
    'tests/test_paths.py',
    'tests/test_nhle_audit.py',
    'tests/test_curation.py',
    'tests/test_terrain_metadata.py',
    'tests/test_background_policy.py',
    'tests/test_terrain_acquisition.py',
    'tests/test_full_terrain_dataset.py',
    'tests/test_terrain_audit.py',
    'tests/test_terrain_index.py',
    'tests/test_terrain_patches.py',
    'tests/test_terrain_qa.py',
    'tests/test_terrain_raster.py',
    'tests/test_terrain_representations.py',
    'tests/test_splits.py',
    'tests/test_dataset_freeze.py',
    'tests/test_model_data.py',
    'tests/test_modelling.py',
    'tests/test_baseline_freeze.py',
    'tests/test_final_evaluation.py',
    'tests/test_robustness.py',
    'tests/test_deep_learning.py',
    'tests/test_cnn_training.py',
    'tests/test_inference.py',
    'outputs/feasibility/bowl_barrow_summary.json',
    'outputs/feasibility/bowl_barrow_counts.csv',
    'outputs/feasibility/bowl_barrow_manual_sample.csv',
    'outputs/feasibility/e001_curation_summary.json',
    'outputs/feasibility/e001_curated_records.csv',
    'outputs/feasibility/e001_group_counts.csv',
    'outputs/feasibility/e001_provenance_summary.csv',
    'outputs/feasibility/e001_second_review_queue.csv',
    'outputs/terrain/e001_pilot_summary.json',
    'outputs/terrain/e001_terrain_index.csv',
    'outputs/terrain/e001_acquisition_estimate.json',
    'outputs/terrain/e001_full_terrain_summary.json',
    'outputs/terrain/e001_full_terrain_audit.json',
    'outputs/terrain/e001_full_terrain_failures.csv',
    'outputs/terrain/e001_overlap_decisions.csv',
    'outputs/background/e001_background_pilot10_summary.json',
    'outputs/background/e001_background_pilot40_summary.json',
    'outputs/background/e001_background_pilot40_visual_qa.json',
    'outputs/background/e001_background_full_summary.json',
    'outputs/background/e001_background_index.csv',
    'outputs/dataset/e001_modelling_index.csv',
    'outputs/dataset/e001_random_split_manifest.json',
    'outputs/dataset/e001_geographic_split_manifest.json',
    'outputs/dataset/e001_dataset_audit.json',
    'outputs/modelling/e001_phase_2d_a_development_results.json',
    'outputs/modelling/e001_primary_baseline_config.json',
    'outputs/modelling/e001_final_results.csv',
    'outputs/modelling/e001_random_vs_geographic.json',
    'outputs/modelling/e001_final_model_audit.json',
    'outputs/modelling/figures/e001_balanced_accuracy_comparison.svg',
    'outputs/modelling/figures/e001_geographic_confusion_matrix.svg',
    'outputs/modelling/figures/e001_random_confusion_matrix.svg',
    'outputs/modelling/figures/e001_roc_curves.svg',
    'outputs/modelling/figures/e001_precision_recall_curves.svg',
    'outputs/robustness/e001_geographic_fold_groups.csv',
    'outputs/robustness/e001_geographic_fold_manifest.json',
    'outputs/robustness/e001_geographic_cv.csv',
    'outputs/robustness/e001_group_performance.csv',
    'outputs/robustness/e001_representation_ablation.csv',
    'outputs/robustness/e001_drop_one_representation.csv',
    'outputs/robustness/e001_seed_sensitivity.csv',
    'outputs/robustness/e001_training_fraction.csv',
    'outputs/robustness/e001_permutation_diagnostic.json',
    'outputs/robustness/e001_robustness_summary.json',
    'outputs/robustness/figures/e001_geographic_fold_balanced_accuracy.svg',
    'outputs/robustness/figures/e001_representation_robustness.svg',
    'outputs/robustness/figures/e001_seed_robustness.svg',
    'outputs/robustness/figures/e001_training_size_learning_curve.svg',
    'outputs/robustness/figures/e001_score_distributions.svg',
    'outputs/deep_learning/e001_cnn_protocol.json',
    'outputs/deep_learning/e001_cnn_fold_results.csv',
    'outputs/deep_learning/e001_cnn_seed_summary.csv',
    'outputs/deep_learning/e001_cnn_training_history.csv',
    'outputs/deep_learning/e001_cnn_group_summary.csv',
    'outputs/deep_learning/e001_cnn_vs_rf.json',
    'outputs/deep_learning/e001_cnn_summary.json',
    'outputs/deep_learning/figures/e001_cnn_vs_rf_by_fold.svg',
    'outputs/deep_learning/figures/e001_cnn_seed_stability.svg',
    'outputs/deep_learning/figures/e001_cnn_training_history.svg',
    'outputs/deep_learning/figures/e001_cnn_confusion_summary.svg',
    'outputs/inference/e001_phase2f_a_readiness.json',
    'outputs/inference/e001_phase2f_b_summary.json',
    'outputs/inference/figures/e001_phase2f_b_score_distribution.svg',
    'website/index.html',
    'website/styles.css',
    'website/site.js',
    'website/README.md',
    'website/assets/favicon.svg',
    'website/assets/terrain-contours.png',
    'website/assets/balanced-accuracy-comparison.svg',
    'website/assets/cnn-vs-rf-by-fold.svg',
    'website/assets/private-inference-score-distribution.svg',
    'tests/test_public_demo.py'
)

$missing = $required | Where-Object { -not (Test-Path $_) }
if ($missing) {
    throw "Missing required research artifacts: $($missing -join ', ')"
}

$readme = Get-Content -Raw 'README.md'
if ($readme -notmatch 'geographically (?:disjoint|separated) holdouts?') {
    throw 'README must state the geographic-holdout principle.'
}
if (
    $readme -notmatch '0\.871 balanced' -or
    $readme -notmatch 'geographically held-out groups' -or
    $readme -notmatch 'has not\s+(?:>\s*)?discovered\s+(?:>\s*)?archaeological sites' -or
    $readme -notmatch '261' -or
    $readme -notmatch '12'
) {
    throw 'README must preserve the verified Phase 2A.5 status and explicit no-claim boundary.'
}

$citation = Get-Content -Raw 'CITATION.cff'
if (
    $citation -notmatch 'cff-version:\s*1\.2\.0' -or
    $citation -notmatch 'repository-code:\s*"https://github\.com/essius10/ArchaeoAI"' -or
    $citation -match '(?m)^\s*(?:doi|license):'
) {
    throw 'CITATION.cff must use verified repository metadata without a DOI or licence claim.'
}

$licensingAudit = Get-Content -Raw 'docs/licensing-and-attribution.md'
if (
    $licensingAudit -notmatch 'does \*\*not\*\* currently have a repository-wide licence' -or
    $licensingAudit -notmatch 'Open Government Licence v3\.0'
) {
    throw 'The licensing audit must preserve the current no-licence status and OGL boundary.'
}

$projectConfig = Get-Content -Raw 'pyproject.toml'
if ($projectConfig -notmatch 'requires-python\s*=\s*">=3\.12,<3\.15"') {
    throw 'pyproject.toml must support Python >=3.12,<3.15.'
}
if ($projectConfig -notmatch 'scikit-learn>=1\.9,<2') {
    throw 'Phase 2D-A must retain the approved scikit-learn modelling dependency.'
}
if ($projectConfig -notmatch 'torch>=2\.13,<2\.14') {
    throw 'Phase 2E-B0 must declare only the approved minimal PyTorch dependency.'
}

$exampleManifest = Get-Content -Raw 'data/manifests/example-dataset.toml'
if ($exampleManifest -notmatch 'status\s*=\s*"template"' -or $exampleManifest -notmatch 'example\.invalid') {
    throw 'The example dataset manifest must remain explicitly fictional and in template status.'
}
$terrainManifest = Get-Content -Raw 'data/manifests/e001-ea-lidar-dtm.toml'
if (
    $terrainManifest -notmatch 'status\s*=\s*"verified"' -or
    $terrainManifest -notmatch 'sensitivity\s*=\s*"sensitive"' -or
    $terrainManifest -notmatch 'requested_records\s*=\s*261' -or
    $terrainManifest -notmatch 'acquired_records\s*=\s*261' -or
    $terrainManifest -notmatch 'rejected_records\s*=\s*0' -or
    $terrainManifest -notmatch 'processing_version\s*=\s*"e001-terrain-v1"' -or
    $terrainManifest -notmatch 'access_date\s*=\s*2026-08-28' -or
    $terrainManifest -notmatch 'sha256\s*=\s*"[0-9a-f]{64}"'
) {
    throw 'The real E001 terrain manifest must describe the verified sensitive 261-site freeze.'
}

$auditSummary = Get-Content -Raw 'outputs/feasibility/bowl_barrow_summary.json' | ConvertFrom-Json
if (
    $auditSummary.privacy.stored_coordinates -ne $false -or
    $auditSummary.privacy.stored_geometry -ne $false -or
    $auditSummary.counts.total_scheduled_monument_records_examined -le 0
) {
    throw 'The Phase 2A summary must be coordinate-free and contain a verified source count.'
}
$aggregateHeaders = (Get-Content 'outputs/feasibility/bowl_barrow_counts.csv' -TotalCount 1)
$manualHeaders = (Get-Content 'outputs/feasibility/bowl_barrow_manual_sample.csv' -TotalCount 1)
if ($aggregateHeaders -match 'Easting|Northing|NGR' -or $manualHeaders -match 'Easting|Northing|NGR') {
    throw 'Tracked Phase 2A CSV outputs must not contain exact-coordinate fields.'
}
$auditCounts = $auditSummary.counts
if (
    $auditCounts.broad_barrow_candidates -ne (
        $auditCounts.probable_bowl_candidates +
        $auditCounts.clear_title_exclusions +
        $auditCounts.manual_review_required
    )
) {
    throw 'Phase 2A triage counts must partition all broad barrow candidates.'
}
$aggregateRows = Import-Csv 'outputs/feasibility/bowl_barrow_counts.csv'
$aggregateProbable = ($aggregateRows | Measure-Object -Property probable_bowl_candidates -Sum).Sum
$aggregateExcluded = ($aggregateRows | Measure-Object -Property clear_title_exclusions -Sum).Sum
$aggregateManual = ($aggregateRows | Measure-Object -Property manual_review_required -Sum).Sum
if (
    $aggregateProbable -ne $auditCounts.probable_bowl_candidates -or
    $aggregateExcluded -ne $auditCounts.clear_title_exclusions -or
    $aggregateManual -ne $auditCounts.manual_review_required
) {
    throw 'Phase 2A aggregate CSV counts must match the JSON summary.'
}
$manualRows = Import-Csv 'outputs/feasibility/bowl_barrow_manual_sample.csv'
$manualIds = @($manualRows.list_entry | Sort-Object)
$sampleIds = @($auditSummary.manual_sample.record_ids | ForEach-Object { "$_" } | Sort-Object)
if ($manualRows.Count -ne $sampleIds.Count -or (Compare-Object $manualIds $sampleIds)) {
    throw 'The manual-review artifact must match the deterministic sample in the JSON summary.'
}

$curationSummary = Get-Content -Raw 'outputs/feasibility/e001_curation_summary.json' | ConvertFrom-Json
$curationCounts = $curationSummary.counts
$curationRows = @(Import-Csv 'outputs/feasibility/e001_curated_records.csv')
if (
    $curationSummary.privacy.stored_coordinates -ne $false -or
    $curationSummary.privacy.stored_geometry -ne $false -or
    $curationRows.Count -ne $curationCounts.records_reviewed
) {
    throw 'The Phase 2A.5 curation output must be complete and coordinate-free.'
}
$statusTotal = (
    $curationCounts.accepted +
    $curationCounts.rejected +
    $curationCounts.uncertain +
    $curationCounts.needs_geometry_review +
    $curationCounts.needs_terrain_review
)
if ($statusTotal -ne $curationCounts.records_reviewed) {
    throw 'Phase 2A.5 review statuses must partition the reviewed queue.'
}
$acceptedRows = @($curationRows | Where-Object { $_.review_status -eq 'accepted' })
if ($acceptedRows.Count -ne $curationCounts.accepted) {
    throw 'Tracked accepted rows must match the Phase 2A.5 summary.'
}
$invalidAccepted = @(
    $acceptedRows | Where-Object {
        $_.bowl_barrow_identity -ne 'yes' -or
        $_.single_monument -ne 'yes' -or
        $_.upstanding_earthwork -ne 'yes' -or
        $_.geometry_qa -ne 'pass' -or
        $_.terrain_coverage -ne 'pass' -or
        $_.terrain_provenance -ne 'pass'
    }
)
if ($invalidAccepted.Count -ne 0) {
    throw 'Every accepted E001 record must pass all six evidence and QA gates.'
}
$trackedCurationHeaders = Get-Content 'outputs/feasibility/e001_curated_records.csv' -TotalCount 1
$curationHeaderFields = @($trackedCurationHeaders -split ',')
if ($curationHeaderFields -match '^(Easting|Northing|NGR|Latitude|Longitude|Geometry|Polygon|BBox)$') {
    throw 'Tracked Phase 2A.5 outputs must not contain exact-coordinate or geometry fields.'
}
$privateIgnoreCheck = & git check-ignore 'data/private/e001-private-sentinel.json'
if ($LASTEXITCODE -ne 0 -or -not $privateIgnoreCheck) {
    throw 'data/private must remain ignored by Git.'
}

$projectRootPath = (Resolve-Path '.').Path
$venvPythonPath = Join-Path $projectRootPath '.venv\Scripts\python.exe'
if ($PythonPath) {
    $pythonExecutable = (Resolve-Path $PythonPath).Path
} elseif (Test-Path $venvPythonPath) {
    $pythonExecutable = (Resolve-Path $venvPythonPath).Path
} else {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($null -eq $pythonCommand) {
        throw 'Python was not found. Create .venv before validating Phase 1.'
    }
    $pythonExecutable = $pythonCommand.Source
}

$runtimeCheck = & $pythonExecutable -c 'import sys; assert sys.implementation.name == "cpython" and (3, 12) <= sys.version_info[:2] < (3, 15); print(f"CPython {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")'
if ($LASTEXITCODE -ne 0) {
    throw 'Python must be a working CPython >=3.12,<3.15 runtime.'
}

$phaseOneCheck = & $pythonExecutable -c 'from pathlib import Path; from archaeoai.config import load_experiment_config; from archaeoai.data.manifest import load_dataset_manifest; root = Path.cwd(); load_experiment_config(root / "configs" / "e001.example.toml"); load_dataset_manifest(root / "data" / "manifests" / "example-dataset.toml"); print("configuration and manifest valid")'
if ($LASTEXITCODE -ne 0) {
    throw 'Phase 1 configuration or manifest validation failed.'
}

$terrainCheck = & $pythonExecutable -c 'import csv, json; from collections import Counter; from pathlib import Path; from archaeoai.data.manifest import load_dataset_manifest; from archaeoai.terrain.privacy import assert_coordinate_safe_mapping; root=Path.cwd(); manifest=load_dataset_manifest(root/"data/manifests/e001-ea-lidar-dtm.toml"); pilot=json.loads((root/"outputs/terrain/e001_pilot_summary.json").read_text()); full=json.loads((root/"outputs/terrain/e001_full_terrain_summary.json").read_text()); audit=json.loads((root/"outputs/terrain/e001_full_terrain_audit.json").read_text()); rows=list(csv.DictReader((root/"outputs/terrain/e001_terrain_index.csv").open(encoding="utf-8-sig"))); failures=list(csv.DictReader((root/"outputs/terrain/e001_full_terrain_failures.csv").open(encoding="utf-8-sig"))); overlaps=list(csv.DictReader((root/"outputs/terrain/e001_overlap_decisions.csv").open(encoding="utf-8-sig"))); [assert_coordinate_safe_mapping(item) for item in (pilot, full, audit)]; [assert_coordinate_safe_mapping(row) for row in rows]; assert manifest.status=="verified" and manifest.sensitivity=="sensitive" and manifest.requested_records==manifest.acquired_records==261 and manifest.rejected_records==0; assert pilot["attempted"]==pilot["passed"]==5 and pilot["rejected"]==0; assert full["counts"]["terrain_passed"]==full["counts"]["representations_passed"]==261 and full["counts"]["terrain_failed"]==full["counts"]["request_retries"]==0; assert audit["cache_revalidation"]["passed"]==audit["cache_revalidation"]["raw_files_present"]==audit["cache_revalidation"]["processed_archives_present"]==261 and audit["cache_revalidation"]["partial_artifacts"]==0; assert audit["visual_qa"]["reviewed"]==audit["visual_qa"]["status_counts"]["pass"]==25 and audit["visual_qa"]["pending"]==audit["visual_qa"]["technical_failures"]==audit["visual_qa"]["manual_review_required"]==0; assert audit["cross_cell"]["patches_passed"]==audit["cross_cell"]["correct_dimensions"]==audit["cross_cell"]["correct_transforms"]==audit["cross_cell"]["representations_passed"]==audit["cross_cell"]["automatic_boundary_checks_passed"]==8 and audit["cross_cell"]["duplicate_rows_or_columns"]==0; assert len(rows)==261 and len(failures)==0 and len(overlaps)==7; assert len({row["sample_id"] for row in rows})==len({row["nhle_list_entry"] for row in rows})==261; assert all(row["qa_status"]==row["raw_qa_status"]==row["representation_qa_status"]=="pass" for row in rows); assert sum(row["cross_cell"].casefold()=="true" for row in rows)==8; components=Counter(row["overlap_group_id"] for row in rows if row["overlap_group_id"]); assert len(components)==7 and set(components.values())=={2}; assert all(row["decision"]=="retain_grouped" for row in overlaps); print("Phase 2B.5 full terrain evidence valid")'
if ($LASTEXITCODE -ne 0) {
    throw 'Phase 2B.5 manifest, acquisition, audit, index, overlap, or privacy validation failed.'
}

$phase2cCheck = & $pythonExecutable -c 'import csv, json; from collections import Counter; from pathlib import Path; from archaeoai.dataset import BACKGROUND_LABEL, POSITIVE_LABEL, read_dataset_index; from archaeoai.splits import validate_frozen_assignment; from archaeoai.terrain.privacy import assert_coordinate_safe_mapping; root=Path.cwd(); records=read_dataset_index(root/"outputs/dataset/e001_modelling_index.csv"); background=list(csv.DictReader((root/"outputs/background/e001_background_index.csv").open(encoding="utf-8-sig"))); full=json.loads((root/"outputs/background/e001_background_full_summary.json").read_text()); visual=json.loads((root/"outputs/background/e001_background_pilot40_visual_qa.json").read_text()); audit=json.loads((root/"outputs/dataset/e001_dataset_audit.json").read_text()); random=json.loads((root/"outputs/dataset/e001_random_split_manifest.json").read_text()); geographic=json.loads((root/"outputs/dataset/e001_geographic_split_manifest.json").read_text()); [assert_coordinate_safe_mapping(item) for item in (full,visual,audit,random,geographic)]; [assert_coordinate_safe_mapping(row) for row in background]; assert len(records)==522 and len(background)==261; assert Counter(row.class_label for row in records)==Counter({POSITIVE_LABEL:261,BACKGROUND_LABEL:261}); assert full["counts"]["terrain_passed"]==full["counts"]["representations_passed"]==261 and full["counts"]["terrain_failed"]==0; assert visual["sample_size"]==visual["passed"]==25 and visual["hard_invalid"]==0; assert audit["counts"]["observation_groups"]==254 and audit["counts"]["overlap_components"]==7; assert all(value==0 for key,value in audit["hard_leakage_audit"].items() if isinstance(value,int)); assert audit["provenance_and_geography_audit"]["class_joint_distribution_exactly_matched"] is True; assert random["frozen"] is True and geographic["frozen"] is True; validate_frozen_assignment(records,condition="random",expected_digest=random["assignment_sha256"]); validate_frozen_assignment(records,condition="geographic",expected_digest=geographic["assignment_sha256"]); assert geographic["final_test_groups"]==["BNG_100KM_E3_N2","BNG_100KM_E5_N4"]; print("Phase 2C dataset and split evidence valid")'
if ($LASTEXITCODE -ne 0) {
    throw 'Phase 2C background, dataset, split, leakage, or privacy validation failed.'
}

$phase2dACheck = & $pythonExecutable -c 'import json; from pathlib import Path; from archaeoai.model_data import authorize_final_test, validate_frozen_primary_config; from archaeoai.terrain.privacy import assert_coordinate_safe_mapping; root=Path.cwd(); result=json.loads((root/"outputs/modelling/e001_phase_2d_a_development_results.json").read_text()); config_path=root/"outputs/modelling/e001_primary_baseline_config.json"; config=validate_frozen_primary_config(config_path); assert_coordinate_safe_mapping(result); assert_coordinate_safe_mapping(config); assert result["condition"]=="geographic" and result["partitions_accessed"]==["train","development"] and result["final_test_accessed"] is False and result["random_condition_evaluated"] is False and len(result["results"])==15; assert all(item["maximum_absolute_class_count_difference"]==0 for fields in result["metadata_shortcut_audit"].values() for item in fields.values()); assert result["scope"]=={"final_accuracy_computed":False,"final_f1_computed":False,"final_roc_auc_computed":False,"predictions_inspected":False}; assert config["model"]=="random_forest" and config["representation"]=="all_four" and config["feature_count"]==4096 and config["classification_threshold"]==0.5 and config["final_test_evaluated"] is False; authorize_final_test(config_path,root/"outputs/dataset/e001_geographic_split_manifest.json",condition="geographic"); print("Phase 2D-A selection evidence valid; immutable pre-unlock state preserved")'
if ($LASTEXITCODE -ne 0) {
    throw 'Phase 2D-A preregistration, development result, frozen configuration, or final-test guard validation failed.'
}

$phase2dBCheck = & $pythonExecutable -c 'import csv, json; from pathlib import Path; from archaeoai.final_evaluation import validate_final_protocol; from archaeoai.terrain.privacy import assert_coordinate_safe_mapping; root=Path.cwd(); protocol,config=validate_final_protocol(root/"configs/e001-phase-2d-b-final-protocol.json",root/"outputs/modelling/e001_primary_baseline_config.json"); result=json.loads((root/"outputs/modelling/e001_random_vs_geographic.json").read_text()); audit=json.loads((root/"outputs/modelling/e001_final_model_audit.json").read_text()); rows=list(csv.DictReader((root/"outputs/modelling/e001_final_results.csv").open(encoding="utf-8"))); assert_coordinate_safe_mapping(result); assert_coordinate_safe_mapping(audit); assert result["final_test_evaluated"] is True and result["selection_commit"]=="790ac9f4b99da94e8f9bab2a6aed70b34ac88558" and result["primary_config_sha256"]==config["config_sha256"] and result["protocol_sha256"]==protocol["protocol_sha256"] and result["no_retuning_declaration"] is True and result["secondary_final_baselines"]==[]; assert len(rows)==2 and {row["condition"] for row in rows}=={"random","geographic"}; random=result["conditions"]["random"]; geographic=result["conditions"]["geographic"]; assert random["counts"]==geographic["counts"]=={"total":62,"positive_bowl_barrow":31,"unlabelled_background":31}; assert random["metrics"]["balanced_accuracy"]==0.8225806451612903 and geographic["metrics"]["balanced_accuracy"]==0.8709677419354839; assert result["random_minus_geographic_balanced_accuracy"]==random["metrics"]["balanced_accuracy"]-geographic["metrics"]["balanced_accuracy"]; assert all(item["valid_replicates"]==5000 and item["undefined_replicates"]==0 for condition in result["conditions"].values() for item in condition["bootstrap"]["intervals"].values()); assert all(condition["terrain_summary_by_correctness"][status]["missing_fraction"]=={"mean":0.0,"median":0.0} for condition in audit["conditions"].values() for status in ("correct","error")); assert audit["privacy"]=={"aggregate_only":True,"coordinates_in_output":False,"sample_identifiers_in_output":False,"maps_created":False} and audit["no_post_final_training_or_tuning"] is True; print("Phase 2D-B final baseline evidence valid; immutable pre-unlock config retained")'
if ($LASTEXITCODE -ne 0) {
    throw 'Phase 2D-B final result, uncertainty, audit, protocol, or privacy validation failed.'
}

$phase2eACheck = & $pythonExecutable -c 'import csv, hashlib, json; from pathlib import Path; from archaeoai.robustness import validate_robustness_protocol; from archaeoai.terrain.privacy import assert_coordinate_safe_mapping; root=Path.cwd(); protocol=validate_robustness_protocol(root/"configs/e001-phase-2e-a-robustness-protocol.json"); manifest=json.loads((root/"outputs/robustness/e001_geographic_fold_manifest.json").read_text()); result=json.loads((root/"outputs/robustness/e001_robustness_summary.json").read_text()); permutation=json.loads((root/"outputs/robustness/e001_permutation_diagnostic.json").read_text()); cv=list(csv.DictReader((root/"outputs/robustness/e001_geographic_cv.csv").open(encoding="utf-8"))); assert_coordinate_safe_mapping(manifest); assert_coordinate_safe_mapping(result); assert_coordinate_safe_mapping(permutation); assert manifest["assignment_sha256"]==protocol["geographic_folds"]["assignment_sha256"] and manifest["integrity"]=={"geographic_groups_kept_whole":True,"matched_and_overlap_units_kept_whole":True,"cross_fold_terrain_window_overlaps":0,"coordinates_written":False,"model_scores_used":False}; assert result["analysis_label"]=="posthoc_geographic_robustness" and result["posthoc_not_confirmatory"] is True and result["original_result_files_unchanged"] is True and result["no_phase_2d_reselection_or_retuning"] is True; assert len(cv)==5 and [round(float(row["balanced_accuracy"]),6) for row in cv]==[0.796296,0.839623,0.79,0.861111,0.83]; assert round(result["primary_geographic_cv"]["summary"]["mean"],6)==0.823406 and result["robustness_classification"]=="ROBUST" and result["recommendation"]=="GO FOR PHASE 2E-B STRONGER MODELS"; assert permutation["runs"]==100 and permutation["used_for_selection_or_tuning"] is False; assert result["shortcut_audit"]["absolute_elevation_in_features"] is False and result["shortcut_audit"]["per_patch_median_normalization_offset_invariance_tested"] is True and result["shortcut_audit"]["sample_id_path_filename_or_serialization_metadata_in_features"] is False and result["shortcut_audit"]["npz_key_order_compression_path_and_name_invariance_tested"] is True and result["shortcut_audit"]["cross_fold_terrain_window_overlaps"]==result["shortcut_audit"]["matched_and_overlap_units_cross_folds"]==0 and result["shortcut_audit"]["metadata_used_as_features"] is False and result["shortcut_audit"]["all_missing_fractions_zero"] is True; assert result["privacy"]=={"aggregate_only":True,"coordinates_written":False,"sample_identifiers_written":False,"maps_created":False}; assert all(hashlib.sha256((root/relative).read_bytes()).hexdigest()==digest for relative,digest in protocol["original_result_file_sha256"].items()); print("Phase 2E-A post-hoc robustness evidence valid; Phase 2D result immutable")'
if ($LASTEXITCODE -ne 0) {
    throw 'Phase 2E-A folds, robustness results, shortcut audits, or Phase 2D immutability validation failed.'
}

$phase2eB0Check = & $pythonExecutable -c 'import hashlib, json; from pathlib import Path; from archaeoai.deep_learning import CNN_INPUT_SHAPE, CompactTerrainCNN, build_fold_partitions, read_cnn_records, read_fold_assignments, trainable_parameter_count, validate_cnn_protocol; from archaeoai.terrain.privacy import assert_coordinate_safe_mapping; root=Path.cwd(); protocol=validate_cnn_protocol(root/"outputs/deep_learning/e001_cnn_protocol.json"); assert_coordinate_safe_mapping(protocol); records=read_cnn_records(root/"outputs/dataset/e001_modelling_index.csv"); assignments=read_fold_assignments(root/"outputs/robustness/e001_geographic_fold_groups.csv"); assert len(records)==522 and len(assignments)==23 and CNN_INPUT_SHAPE==(4,128,128) and trainable_parameter_count(CompactTerrainCNN())==59145; partitions=[build_fold_partitions(records,assignments,held_out_fold=fold) for fold in range(5)]; assert all(len(item.internal_train)+len(item.internal_validation)+len(item.held_out)==522 for item in partitions); assert all(not ({row.geographic_block_id for row in item.internal_validation}&{row.geographic_block_id for row in item.held_out}) for item in partitions); assert protocol["status"]=="READY_NOT_TRAINED" and protocol["execution_state"]=={"real_e001_samples_loaded_by_cnn":False,"cnn_trained":False,"geographic_cv_run":False,"cnn_performance_metrics_computed":False,"random_forest_comparison_performed":False}; serialized=json.dumps(protocol,sort_keys=True).casefold(); assert "balanced_accuracy" not in serialized and "roc_auc" not in serialized; immutable={"outputs/modelling/e001_final_results.csv":"28b7503965ea75143616f5e726890b842030a20be8c283e2e9a7dd3c540e39a6","outputs/modelling/e001_random_vs_geographic.json":"6d6d8cf9ebca15d7cf28c99e9d05d9b94b5837695aaf29a973c80d708aad9055","outputs/modelling/e001_final_model_audit.json":"ad1204c002b6eb591b9ccf8cfdc89021ffcc6f8b709b30aae6fefd0ec9e891c2","outputs/robustness/e001_robustness_summary.json":"6ebf881562458110562e7181824c677acf7ecfa7edc673152e96bf1a7c319591","outputs/robustness/e001_geographic_fold_manifest.json":"2575232a392925eedcbabe343e599df58a789137bad3b356b3774e9ef9637157"}; assert all(hashlib.sha256((root/path).read_bytes()).hexdigest()==digest for path,digest in immutable.items()); print("Phase 2E-B0 CNN protocol valid; READY_NOT_TRAINED; Phase 2D/2E-A immutable")'
if ($LASTEXITCODE -ne 0) {
    throw 'Phase 2E-B0 CNN protocol, fold reuse, privacy, or immutability validation failed.'
}

$phase2eBCheck = & $pythonExecutable -c 'import csv,json; from pathlib import Path; from archaeoai.terrain.privacy import assert_coordinate_safe_mapping; root=Path.cwd(); summary=json.loads((root/"outputs/deep_learning/e001_cnn_summary.json").read_text()); comparison=json.loads((root/"outputs/deep_learning/e001_cnn_vs_rf.json").read_text()); runs=list(csv.DictReader((root/"outputs/deep_learning/e001_cnn_fold_results.csv").open(encoding="utf-8"))); seeds=list(csv.DictReader((root/"outputs/deep_learning/e001_cnn_seed_summary.csv").open(encoding="utf-8"))); history=list(csv.DictReader((root/"outputs/deep_learning/e001_cnn_training_history.csv").open(encoding="utf-8"))); groups=list(csv.DictReader((root/"outputs/deep_learning/e001_cnn_group_summary.csv").open(encoding="utf-8"))); assert_coordinate_safe_mapping(summary); assert_coordinate_safe_mapping(comparison); assert summary["status"]=="COMPLETE" and summary["analysis_label"]=="posthoc_stronger_model_geographic_cv" and summary["protocol_sha256"]=="6007a2b62157195c26a05474935d88f1e3ed7b6c6780572f35c1162ab08d39c0" and summary["fold_assignment_sha256"]=="825eb1088a53f764f991bf6bb22f2c9fe6eeb868916a5abab92012eed85d90ab" and summary["no_retuning_declaration"] is True and summary["primary_runs_completed"]==15; assert len(runs)==15 and {(row["fold"],int(row["seed"])) for row in runs}=={(f"fold_{fold}",seed) for fold in range(1,6) for seed in (20260829,20260830,20260831)}; assert len(seeds)==3 and len(history)>0 and len(groups)==23; assert round(summary["fold_mean_balanced_accuracy"]["mean"],6)==0.700866 and round(comparison["rf_mean_balanced_accuracy"],6)==0.823406 and round(comparison["cnn_minus_rf"],6)==-0.122540; assert [round(row["cnn_mean_balanced_accuracy"],6) for row in comparison["folds"]]==[0.756173,0.660377,0.69,0.694444,0.703333]; assert summary["aggregate_confusion_across_15_runs"]=={"tn":532,"fp":251,"fn":217,"tp":566}; assert summary["training_diagnostics"]["early_stopped_runs"]==15 and summary["training_diagnostics"]["class_collapsed_runs"]==0; assert summary["technical_failures"]==[] and summary["secondary_preregistered_conditions"]==summary["secondary_conditions_run"]==[]; assert summary["stronger_model_classification"]=="CNN NOT JUSTIFIED AT CURRENT DATA SCALE" and summary["phase_2f_recommendation"]=="USE RANDOM FOREST FOR PHASE 2F"; assert summary["privacy"]=={"coordinates_written":False,"sample_identifiers_written":False,"sample_predictions_written":False,"checkpoints_private_and_ignored":True,"maps_created":False}; print("Phase 2E-B 15-run CNN evidence valid; no retuning; Random Forest retained")'
if ($LASTEXITCODE -ne 0) {
    throw 'Phase 2E-B CNN results, classification, privacy, or no-retuning validation failed.'
}

$phase2fACheck = & $pythonExecutable -c 'import hashlib,json; from pathlib import Path; from archaeoai.inference import validate_inference_protocol; from archaeoai.terrain.privacy import assert_coordinate_safe_mapping; root=Path.cwd(); protocol=validate_inference_protocol(root/"configs/e001-phase-2f-a-inference-protocol.json"); assert_coordinate_safe_mapping(protocol); assert protocol["protocol_sha256"]=="fa1f9cd12230df3f7c83c45febd5ec0ba751f371a098600873380bc47c624095" and protocol["status"]=="READY_NO_REAL_SCAN" and protocol["primary_config_sha256"]=="20cd377c17373eeeb5403c84119084287f193d93b42c8004d99c823e01a157e4"; assert protocol["model"]["parameters"]=={"n_estimators":300,"max_depth":8,"min_samples_leaf":5,"max_features":"sqrt","n_jobs":1,"random_state":20260829} and protocol["model"]["training_observations"]==522 and protocol["model"]["training_class_counts"]=={"positive_bowl_barrow":261,"unlabelled_background":261} and protocol["model"]["model_state_sha256"]=="e3b0c072f437e889f09a2a2cf5a37f19b2f483eb5188e102b132a89ee76d1939" and protocol["model"]["candidate_result_retraining_allowed"] is False; assert protocol["patch_generation"]["patch_dimensions_m"]==[128,128] and protocol["patch_generation"]["stride_m"]==64 and protocol["patch_generation"]["maximum_complete_domain_windows_before_QA"]==5929 and protocol["preprocessing"]["feature_count"]==4096; assert protocol["controlled_domain"]["maximum_domains"]==1 and protocol["controlled_domain"]["domain_binding_status"]=="NOT_YET_BOUND" and protocol["privacy"]["tracked_outputs_aggregate_only"] is True and protocol["privacy"]["tracked_coordinates_NGR_GeoJSON_or_candidate_identifiers"] is False; assert protocol["score_semantics"]["binary_site_decision"] is False and protocol["score_semantics"]["calibration_claimed"] is False; assert protocol["execution_state"]=={"full_E001_RF_fit_completed":True,"new_terrain_loaded":False,"new_terrain_scored":False,"real_candidate_scan_completed":False,"candidate_scores_computed":False,"candidate_locations_created":False,"candidate_locations_exposed":False,"website_or_API_built":False}; assert all(hashlib.sha256((root/path).read_bytes()).hexdigest()==digest for path,digest in protocol["immutable_artifact_sha256"].items()); print("Phase 2F-A controlled-inference protocol valid; full E001 RF fit frozen; no real scan")'
if ($LASTEXITCODE -ne 0) {
    throw 'Phase 2F-A protocol, frozen RF fit, privacy, or immutable-artifact validation failed.'
}

$phase2fASmokeCheck = & $pythonExecutable -c 'import json; from pathlib import Path; from archaeoai.terrain.privacy import assert_coordinate_safe_mapping; root=Path.cwd(); receipt=json.loads((root/"outputs/inference/e001_phase2f_a_readiness.json").read_text()); assert_coordinate_safe_mapping(receipt); assert receipt["status"]=="READY_NO_REAL_SCAN" and receipt["protocol_sha256"]=="fa1f9cd12230df3f7c83c45febd5ec0ba751f371a098600873380bc47c624095" and receipt["benchmark_scope"]=="synthetic_coordinate_free_CPU_smoke_only"; assert receipt["synthetic_patch_count"]==32 and receipt["model_patches_per_second"]>0 and receipt["end_to_end_patches_per_second"]>0 and receipt["private_model_size_bytes"]>0 and receipt["process_peak_working_set_bytes"]>0; assert receipt["CPU_feasibility"] is True and receipt["GPU_required"] is False and receipt["privacy"]=={"real_terrain_loaded":False,"real_candidate_scan_completed":False,"candidate_locations_created":False,"candidate_locations_exposed":False,"synthetic_per_patch_scores_written":False,"aggregate_only":True}; print("Phase 2F-A coordinate-free synthetic CPU smoke evidence valid; no real candidate scan")'
if ($LASTEXITCODE -ne 0) {
    throw 'Phase 2F-A synthetic smoke, performance, or privacy validation failed.'
}

$phase2fBCheck = & $pythonExecutable -c 'import json; from pathlib import Path; from archaeoai.terrain.privacy import assert_coordinate_safe_mapping; root=Path.cwd(); result=json.loads((root/"outputs/inference/e001_phase2f_b_summary.json").read_text()); assert_coordinate_safe_mapping(result); assert result["status"]=="READY_FOR_BLINDED_HUMAN_MORPHOLOGY_REVIEW" and result["protocol_sha256"]=="fa1f9cd12230df3f7c83c45febd5ec0ba751f371a098600873380bc47c624095" and result["primary_config_sha256"]=="20cd377c17373eeeb5403c84119084287f193d93b42c8004d99c823e01a157e4" and result["model_state_sha256"]=="e3b0c072f437e889f09a2a2cf5a37f19b2f483eb5188e102b132a89ee76d1939"; assert result["total_windows"]==result["valid_windows"]==5929 and result["rejected_windows"]==result["no_data_windows"]==0 and result["deduplicated_representatives"]==1159; assert result["review_queue_counts"]=={"highest_score":12,"medium_score_diagnostic":25,"random_reference":25} and result["private_score_table_sha256"]=="78434f3518bd8aa5fb83e3dd9f7c3d54288e1f31a5e61618df4541bb40977771" and result["score_table_frozen_before_interpretation"] is True; assert result["pipeline"]["model_retrained_or_tuned"] is False and result["controlled_domain"]["count"]==1 and result["controlled_domain"]["training_or_evaluation_overlap"] is False; assert result["review"]["blinded_packet_status"]=="READY_UNREVIEWED" and result["review"]["blinded_packet_items"]==62 and result["review"]["human_morphology_review_performed"] is False and result["review"]["heritage_record_cross_check_performed"] is False; assert result["interpretation"]["archaeological_probability_claimed"] is False and result["interpretation"]["discovery_claimed"] is False; assert result["privacy"]["aggregate_only"] is True and result["privacy"]["coordinates_committed"] is False; print("Phase 2F-B aggregate evidence valid; private score table frozen; blinded review pending")'
if ($LASTEXITCODE -ne 0) {
    throw 'Phase 2F-B aggregate result, frozen score receipt, privacy, or review boundary validation failed.'
}

$terrainIndexHeader = Get-Content 'outputs/terrain/e001_terrain_index.csv' -TotalCount 1
if ($terrainIndexHeader -match '(?i)easting|northing|ngr|latitude|longitude|geometry|polygon|bbox|bounds|centre|center') {
    throw 'The tracked terrain index contains a coordinate-bearing field.'
}
$backgroundIndexHeader = Get-Content 'outputs/background/e001_background_index.csv' -TotalCount 1
$datasetIndexHeader = Get-Content 'outputs/dataset/e001_modelling_index.csv' -TotalCount 1
if (
    $backgroundIndexHeader -match '(?i)easting|northing|ngr|latitude|longitude|geometry|polygon|bbox|bounds|centre|center' -or
    $datasetIndexHeader -match '(?i)easting|northing|ngr|latitude|longitude|geometry|polygon|bbox|bounds|centre|center'
) {
    throw 'A tracked Phase 2C index contains a coordinate-bearing field.'
}
$modellingOutputs = Get-Content -Raw 'outputs/modelling/e001_phase_2d_a_development_results.json', 'outputs/modelling/e001_primary_baseline_config.json', 'outputs/modelling/e001_random_vs_geographic.json', 'outputs/modelling/e001_final_model_audit.json'
if ($modellingOutputs -match '(?i)"(?:easting|northing|ngr|latitude|longitude|geometry|polygon|bbox|bounds|centre|center)"\s*:') {
    throw 'A tracked Phase 2D-A output contains a coordinate-bearing field.'
}
$robustnessOutputs = Get-Content -Raw 'outputs/robustness/*.json', 'outputs/robustness/*.csv', 'outputs/robustness/figures/*.svg'
if ($robustnessOutputs -match '(?i)"(?:easting|northing|ngr|latitude|longitude|geometry|polygon|bbox|bounds|centre|center|sample_id)"\s*:') {
    throw 'A tracked Phase 2E-A output contains a coordinate or sample identifier.'
}
$deepLearningOutputs = Get-Content -Raw 'outputs/deep_learning/*.json', 'outputs/deep_learning/*.csv', 'outputs/deep_learning/figures/*.svg'
if ($deepLearningOutputs -match '(?i)"(?:easting|northing|ngr|latitude|longitude|geometry|polygon|bbox|bounds|centre|center|sample_id)"\s*:') {
    throw 'A tracked Phase 2E-B0 output contains a coordinate or sample identifier.'
}
$inferenceOutputs = Get-Content -Raw 'outputs/inference/*.json', 'outputs/inference/figures/*.svg'
if ($inferenceOutputs -match '(?i)"(?:easting|northing|ngr|latitude|longitude|geometry|polygon|bbox|bounds|centre|center|sample_id|private_token)"\s*:') {
    throw 'A tracked Phase 2F output contains a coordinate or private identifier.'
}
$trackedSensitive = @(& git ls-files -- '*.tif' '*.tiff' '*.las' '*.laz' '*.gpkg' '*.shp' '*.npy' '*.npz' '*.pt' '*.pth' '*.ckpt' 'data/private/**' 'data/raw/**' 'data/interim/**' 'data/processed/**')
if ($LASTEXITCODE -ne 0 -or $trackedSensitive.Count -ne 0) {
    throw "Sensitive or bulk terrain is tracked: $($trackedSensitive -join ', ')"
}
$privateTerrainIgnoreCheck = & git check-ignore 'data/private/e001/terrain/raw/private-sentinel.tif'
if ($LASTEXITCODE -ne 0 -or -not $privateTerrainIgnoreCheck) {
    throw 'Private E001 terrain must remain ignored by Git.'
}
$privateBackgroundIgnoreCheck = & git check-ignore 'data/private/e001/backgrounds/private-sentinel.json'
if ($LASTEXITCODE -ne 0 -or -not $privateBackgroundIgnoreCheck) {
    throw 'Private E001 background coordinates and terrain must remain ignored by Git.'
}
$checkpointIgnoreCheck = & git check-ignore 'outputs/deep_learning/private-sentinel.pt'
if ($LASTEXITCODE -ne 0 -or -not $checkpointIgnoreCheck) {
    throw 'PyTorch checkpoints must remain ignored by Git.'
}
$trainingRunIgnoreCheck = & git check-ignore 'outputs/deep_learning/training_runs/private-sentinel.json'
if ($LASTEXITCODE -ne 0 -or -not $trainingRunIgnoreCheck) {
    throw 'Private deep-learning training histories must remain ignored by Git.'
}

$publicDemo = Get-Content -Raw 'website/index.html'
if (
    $publicDemo -notmatch '87\.1' -or
    $publicDemo -notmatch '82\.3%' -or
    $publicDemo -notmatch '70\.1%' -or
    $publicDemo -notmatch 'No human morphology review has been completed' -or
    $publicDemo -notmatch 'No heritage cross-check has occurred' -or
    $publicDemo -notmatch 'Predictions are not discoveries'
) {
    throw 'The public demo must preserve verified aggregate results and research boundaries.'
}
$publicDemoText = Get-Content -Raw 'website/*.html', 'website/*.css', 'website/*.js', 'website/*.json', 'website/*.xml', 'website/*.md'
if (
    $publicDemoText -match '(?i)["''](?:easting|northing|latitude|longitude|geometry|polygon|bbox|bounds|private_token|sample_id)["'']\s*:' -or
    $publicDemoText -match 'BNG_100KM_E\d+_N\d+'
) {
    throw 'The public demo contains a coordinate-bearing or private identifier field.'
}
$publicDemoSensitive = @(Get-ChildItem 'website' -Recurse -File | Where-Object {
    $_.Extension -in @('.tif', '.tiff', '.las', '.laz', '.gpkg', '.shp', '.npy', '.npz', '.pt', '.pth', '.ckpt', '.geojson')
})
if ($publicDemoSensitive.Count -ne 0) {
    throw "The public demo contains sensitive or candidate-level files: $($publicDemoSensitive.FullName -join ', ')"
}
$publicFigureCopies = @{
    'website/assets/balanced-accuracy-comparison.svg' = 'outputs/modelling/figures/e001_balanced_accuracy_comparison.svg'
    'website/assets/cnn-vs-rf-by-fold.svg' = 'outputs/deep_learning/figures/e001_cnn_vs_rf_by_fold.svg'
    'website/assets/private-inference-score-distribution.svg' = 'outputs/inference/figures/e001_phase2f_b_score_distribution.svg'
}
foreach ($copy in $publicFigureCopies.Keys) {
    $copyHash = (Get-FileHash -Algorithm SHA256 $copy).Hash
    $sourceHash = (Get-FileHash -Algorithm SHA256 $publicFigureCopies[$copy]).Hash
    if ($copyHash -ne $sourceHash) {
        throw "Public aggregate figure differs from its frozen source: $copy"
    }
}
$publicDemoCheck = 'public demo aggregate claims, privacy boundary, and frozen figure copies valid'

Write-Output "Validation passed: $($required.Count) required artifacts; $runtimeCheck; $phaseOneCheck; $terrainCheck; $phase2cCheck; $phase2dACheck; $phase2dBCheck; $phase2eACheck; $phase2eB0Check; $phase2eBCheck; $phase2fACheck; $phase2fASmokeCheck; $phase2fBCheck; $publicDemoCheck."
