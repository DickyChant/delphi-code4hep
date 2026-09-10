import os

import FWCore.ParameterSet.Config as cms
from FWCore.Modules.modules import EmptySource
from Code4hep.G4Application.modules import G4SimProducer
from Code4hep.Generators.modules import GenProducer

process = cms.Process("DELPHITRACKING")
process.source = EmptySource()
process.maxEvents.input = int(os.environ.get("C4H_MAX_EVENTS", "1"))
process.options.numberOfThreads = 1
process.options.numberOfStreams = 1

process.gen = GenProducer(
    generatorType=cms.string("HepMC3Generator"),
    generator=cms.InputTag("MCParticles"),
    initialSeed=cms.uint32(12345),
    Verbosity=cms.untracked.int32(0),
    PartID=cms.untracked.int32(13),
    MinPt=cms.double(10.0),
    MaxPt=cms.double(10.0),
    MinEta=cms.double(0.5),
    MaxEta=cms.double(0.5),
    MinPhi=cms.double(0.0),
    MaxPhi=cms.double(0.0),
)

process.sim = G4SimProducer(
    generator=cms.InputTag("gen", "MCParticles"),
    randomSeed=cms.uint32(67890),
    Physics=cms.PSet(type=cms.string("FTFP_BERT")),
    Detector=cms.PSet(
        gdml=cms.string(os.environ["C4H_GDML"]),
        magneticFieldTesla=cms.double(float(os.environ["C4H_FIELD_TESLA"])),
    ),
)

process.trackerPartitions = cms.EDProducer(
    "delphi_edm4hep::DelphiTrackerHitPartitionProducer",
    simTrackerHits=cms.InputTag("sim", "SimTrackerHits"),
)

process.vertexDigis = cms.EDProducer(
    "delphi_edm4hep::DelphiVertexDigitizerProducer",
    simTrackerHits=cms.InputTag("trackerPartitions", "VertexSimHits"),
    cargoSnapshot=cms.string(os.environ["C4H_DELPHI_CARGO"]),
    randomSeed=cms.uint32(13579),
)

process.vertexHits = cms.EDProducer(
    "delphi_edm4hep::DelphiVertexHitReconstructionProducer",
    digis=cms.InputTag("vertexDigis", "VertexDigis"),
    digiTruthLinks=cms.InputTag(
        "vertexDigis", "VertexDigiSimTrackerHitLinks"
    ),
    cargoSnapshot=cms.string(os.environ["C4H_DELPHI_CARGO"]),
)

process.innerDetectorDigis = cms.EDProducer(
    "delphi_edm4hep::DelphiInnerDetectorDigitizerProducer",
    simTrackerHits=cms.InputTag(
        "trackerPartitions", "InnerDetectorSimHits"
    ),
    cargoSnapshot=cms.string(os.environ["C4H_DELPHI_CARGO"]),
    magneticFieldTesla=cms.double(float(os.environ["C4H_FIELD_TESLA"])),
    randomSeed=cms.uint32(24680),
    wireEfficiency=cms.double(0.80),
    transverseResolutionCm=cms.double(0.0100),
)

process.innerDetectorHits = cms.EDProducer(
    "delphi_edm4hep::DelphiInnerDetectorHitReconstructionProducer",
    digis=cms.InputTag("innerDetectorDigis", "InnerDetectorJetDigis"),
    digiTruthLinks=cms.InputTag(
        "innerDetectorDigis", "InnerDetectorDigiSimTrackerHitLinks"
    ),
    cargoSnapshot=cms.string(os.environ["C4H_DELPHI_CARGO"]),
    magneticFieldTesla=cms.double(float(os.environ["C4H_FIELD_TESLA"])),
    transverseResolutionCm=cms.double(0.0100),
)

process.tpcDigis = cms.EDProducer(
    "delphi_edm4hep::DelphiTpcDigitizerProducer",
    simTrackerHits=cms.InputTag("trackerPartitions", "TpcSimHits"),
    cargoSnapshot=cms.string(os.environ["C4H_DELPHI_CARGO"]),
    randomSeed=cms.uint32(24680),
    electronEnergyEv=cms.double(20.0),
    avalancheScale=cms.double(0.016),
    magneticFieldTesla=cms.double(float(os.environ["C4H_FIELD_TESLA"])),
)

process.tpcHits = cms.EDProducer(
    "delphi_edm4hep::DelphiTpcHitReconstructionProducer",
    digis=cms.InputTag("tpcDigis", "TpcDigis"),
    digiTruthLinks=cms.InputTag("tpcDigis", "TpcDigiSimTrackerHitLinks"),
    cargoSnapshot=cms.string(os.environ["C4H_DELPHI_CARGO"]),
)

process.centralTracks = cms.EDProducer(
    "delphi_edm4hep::DelphiCentralTrackFitProducer",
    tpcHits=cms.InputTag("tpcHits", "TpcHits"),
    minimumRows=cms.uint32(8),
    transverseSigmaMm=cms.double(5.0),
    longitudinalSigmaMm=cms.double(10.0),
    constrainToInteractionPoint=cms.bool(True),
)

process.outerDetectorDigis = cms.EDProducer(
    "delphi_edm4hep::DelphiOuterDetectorDigitizerProducer",
    simTrackerHits=cms.InputTag(
        "trackerPartitions", "OuterDetectorSimHits"
    ),
    cargoSnapshot=cms.string(os.environ["C4H_DELPHI_CARGO"]),
    randomSeed=cms.uint32(97531),
)

process.outerDetectorHits = cms.EDProducer(
    "delphi_edm4hep::DelphiOuterDetectorHitReconstructionProducer",
    digis=cms.InputTag("outerDetectorDigis", "OuterDetectorDigis"),
    digiTruthLinks=cms.InputTag(
        "outerDetectorDigis", "OuterDetectorDigiSimTrackerHitLinks"
    ),
    cargoSnapshot=cms.string(os.environ["C4H_DELPHI_CARGO"]),
)

process.output = cms.OutputModule(
    "PodioOutputModule",
    fileName=cms.untracked.string(os.environ["C4H_OUTPUT"]),
)

process.generation_step = cms.Path(process.gen)
process.simulation_step = cms.Path(process.sim)
process.partition_step = cms.Path(process.trackerPartitions)
process.vertex_digitization_step = cms.Path(process.vertexDigis)
process.vertex_reconstruction_step = cms.Path(process.vertexHits)
process.inner_detector_digitization_step = cms.Path(
    process.innerDetectorDigis
)
process.inner_detector_reconstruction_step = cms.Path(
    process.innerDetectorHits
)
process.tpc_digitization_step = cms.Path(process.tpcDigis)
process.tpc_reconstruction_step = cms.Path(process.tpcHits)
process.central_track_fit_step = cms.Path(process.centralTracks)
process.outer_detector_digitization_step = cms.Path(
    process.outerDetectorDigis
)
process.outer_detector_reconstruction_step = cms.Path(
    process.outerDetectorHits
)
process.output_step = cms.EndPath(process.output)
process.schedule = cms.Schedule(
    process.generation_step,
    process.simulation_step,
    process.partition_step,
    process.vertex_digitization_step,
    process.vertex_reconstruction_step,
    process.inner_detector_digitization_step,
    process.inner_detector_reconstruction_step,
    process.tpc_digitization_step,
    process.tpc_reconstruction_step,
    process.central_track_fit_step,
    process.outer_detector_digitization_step,
    process.outer_detector_reconstruction_step,
    process.output_step,
)
