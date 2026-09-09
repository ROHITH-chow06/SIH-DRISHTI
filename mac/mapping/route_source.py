from abc import ABC, abstractmethod
from typing import List, Dict, Any
from core.models import CandidateRoadSegment, Position

class CandidateRouteSource(ABC):
    @abstractmethod
    def load_routes(self) -> List[CandidateRoadSegment]:
        pass

class DemoRouteSource(CandidateRouteSource):
    """
    Generates dummy candidate routes inside the Deposit-5 site.
    These are DEMO candidate paths, NOT real Sentinel-1 extracted roads.
    """
    def load_routes(self) -> List[CandidateRoadSegment]:
        return [
            CandidateRoadSegment(
                route_id="DEMO_HAUL_MAIN_01",
                path_coordinates=[
                    Position(latitude=18.67, longitude=81.185),
                    Position(latitude=18.671, longitude=81.1855),
                    Position(latitude=18.6725, longitude=81.1865),
                    Position(latitude=18.674, longitude=81.187),
                    Position(latitude=18.675, longitude=81.188),
                    Position(latitude=18.6755, longitude=81.1895),
                    Position(latitude=18.6765, longitude=81.1905),
                    Position(latitude=18.678, longitude=81.1915),
                    Position(latitude=18.6795, longitude=81.1925),
                    Position(latitude=18.6805, longitude=81.192),
                    Position(latitude=18.6815, longitude=81.193),
                    Position(latitude=18.682072, longitude=81.193572),
                    Position(latitude=18.683, longitude=81.1945),
                    Position(latitude=18.6845, longitude=81.195),
                    Position(latitude=18.686, longitude=81.1955),
                    Position(latitude=18.6875, longitude=81.1965),
                    Position(latitude=18.6885, longitude=81.1975),
                    Position(latitude=18.69, longitude=81.1985),
                    Position(latitude=18.692, longitude=81.1995),
                    Position(latitude=18.694, longitude=81.201),
                    Position(latitude=18.696, longitude=81.203)
                ],
                source="DEMO_CANDIDATE",
                confidence=0.1,
                status="CANDIDATE"
            ),
            CandidateRoadSegment(
                route_id="DEMO_HAUL_SEC_01",
                path_coordinates=[
                    Position(latitude=18.682072, longitude=81.193572),
                    Position(latitude=18.6825, longitude=81.192),
                    Position(latitude=18.6835, longitude=81.19),
                    Position(latitude=18.683, longitude=81.1885),
                    Position(latitude=18.682, longitude=81.187),
                    Position(latitude=18.6805, longitude=81.185),
                    Position(latitude=18.679, longitude=81.183),
                    Position(latitude=18.6775, longitude=81.181),
                    Position(latitude=18.676, longitude=81.18)
                ],
                source="DEMO_CANDIDATE",
                confidence=0.1,
                status="CANDIDATE"
            ),
            CandidateRoadSegment(
                route_id="DEMO_HAUL_LOOP_01",
                path_coordinates=[
                    Position(latitude=18.676, longitude=81.18),
                    Position(latitude=18.675, longitude=81.181),
                    Position(latitude=18.6735, longitude=81.183),
                    Position(latitude=18.672, longitude=81.1855),
                    Position(latitude=18.671, longitude=81.1855)
                ],
                source="DEMO_CANDIDATE",
                confidence=0.1,
                status="CANDIDATE"
            )
        ]

def extract_candidate_routes_from_sar(raster_path: str) -> List[CandidateRoadSegment]:
    """
    Future hook to extract candidate roads from actual Sentinel-1 GeoTIFF.
    """
    raise NotImplementedError("SAR raster unavailable")
