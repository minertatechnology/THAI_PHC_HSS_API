from pydantic import BaseModel

class OsmGenderSummary(BaseModel):
    province_code: str
    province_name_th: str
    district_code: str
    district_name_th: str
    subdistrict_code: str
    subdistrict_name_th: str
    total_count: int
    male_count: int
    female_count: int
