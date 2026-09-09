import pytest
from mapping.sar_layer import SARLayer
from core.models import SARMetadata
from core.config import SAR_BBOX

def test_sar_layer_initialization():
    layer = SARLayer()
    assert layer._metadata is None
    
def test_sar_layer_metadata():
    layer = SARLayer()
    meta = layer.get_metadata()
    
    assert isinstance(meta, SARMetadata)
    assert meta.product_id == "S1D_IW_GRDH_1SDV_20260829T002946_20260829T003011_004333_007FEA_20B4_COG.SAFE"
    assert meta.polarization == "VV+VH"
    assert meta.bbox == SAR_BBOX
    assert meta.source == "Copernicus Data Space"
    
    # Should cache it
    meta2 = layer.get_metadata()
    assert meta is meta2
