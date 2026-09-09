from typing import Optional
from datetime import datetime
from core.models import SARMetadata
from core.config import SAR_BBOX, SAR_SITE_NAME

class SARLayer:
    """
    Manages the Sentinel-1 SAR mapping layer.
    Retrieves and caches metadata from the Copernicus Data Space API.
    Does NOT download the massive raster, provides a prototype overlay bounding box.
    """
    def __init__(self):
        self._metadata: Optional[SARMetadata] = None

    def get_metadata(self) -> SARMetadata:
        """
        Returns the SAR metadata. In this prototype, we return the verified 
        Deposit-5 scene metadata directly as if cached from the API.
        """
        if self._metadata is None:
            # We would normally query Copernicus Data Space OData API here.
            # Using the validated scene from Step 7A plan.
            self._metadata = SARMetadata(
                product_id="S1D_IW_GRDH_1SDV_20260829T002946_20260829T003011_004333_007FEA_20B4_COG.SAFE",
                acquisition_time=datetime.fromisoformat("2026-08-29T00:29:46+00:00"),
                polarization="VV+VH",
                bbox=SAR_BBOX,
                source="Copernicus Data Space"
            )
        return self._metadata
