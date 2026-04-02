from __future__ import annotations

import random
import uuid
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple


class MockDataStore:
    """Central in-memory store for demo data used by the mock API endpoints."""

    _initialized: bool = False

    # Core datasets
    volunteers: Dict[str, Dict[str, Any]] = {}
    volunteer_history: Dict[str, List[Dict[str, Any]]] = {}
    meta_options: Dict[str, List[Dict[str, str]]] = {}

    areas: Dict[str, Dict[str, Dict[str, Any]]] = {
        "provinces": {},
        "districts": {},
        "subdistricts": {},
        "villages": {},
        "communities": {},
    }

    announcements: Dict[str, Dict[str, Any]] = {}
    announcement_reads: Dict[str, set[str]] = {}

    groups: Dict[str, Dict[str, Any]] = {}
    main_menus: Dict[str, Dict[str, Any]] = {}
    sub_menus: Dict[str, Dict[str, Any]] = {}
    menu_assignees: Dict[str, set[str]] = {}

    roles: Dict[str, Dict[str, Any]] = {}
    role_permissions: Dict[str, Dict[str, bool]] = {}

    users: Dict[str, Dict[str, Any]] = {}

    reports: Dict[str, List[Dict[str, Any]]] = {}

    @classmethod
    def ensure_initialized(cls) -> None:
        if cls._initialized:
            return

        random.seed(42)
        cls._seed_meta()
        cls._seed_areas()
        cls._seed_groups_and_menus()
        cls._seed_roles()
        cls._seed_users()
        cls._seed_volunteers()
        cls._seed_announcements()
        cls._seed_reports()

        cls._initialized = True

    # ------------------------------------------------------------------
    # Seeding helpers
    # ------------------------------------------------------------------
    @classmethod
    def _seed_meta(cls) -> None:
        cls.meta_options = {
            "prefixes": cls._to_options(["Mr.", "Mrs.", "Ms."]),
            "genders": cls._to_options(["Male", "Female", "Other"]),
            "education-levels": cls._to_options(["Primary", "Secondary", "Bachelor", "Master"]),
            "marital-status": cls._to_options(["Single", "Married", "Divorced"]),
            "occupations": cls._to_options(["Farmer", "Teacher", "Nurse", "Engineer"]),
            "religions": cls._to_options(["Buddhism", "Islam", "Christianity"]),
            "banks": cls._to_options(["BAAC", "SCB", "Krungthai"]),
            "health-facilities": cls._to_options(["Clinic", "Community Hospital", "Regional Hospital"]),
            "children-count": cls._to_options(["0", "1", "2", "3", "4+"]),
            "positions": cls._to_options(["Member", "Leader", "Deputy Leader"]),
            "specialties": cls._to_options(["First Aid", "Nutrition", "Elderly Care"]),
            "osmo-club-positions": cls._to_options(["President", "Secretary", "Treasurer"]),
            "vaccine-types": cls._to_options(["COVID-19", "Flu", "Tetanus"]),
            "training-courses": cls._to_options(["Basic Care", "Advanced Care", "Community Outreach"]),
            "nfe-levels": cls._to_options(["Level 1", "Level 2", "Level 3"]),
            "award-levels": cls._to_options(["Gold", "Silver", "Bronze"]),
            "award-categories": cls._to_options(["Community", "Health", "Education"]),
            "resignation-reasons": cls._to_options(["Health", "Relocation", "Family"]),
            "activity-locations": cls._to_options(["Community Hall", "School", "Temple"]),
        }

    @classmethod
    def _seed_areas(cls) -> None:
        for province_index, province_name in enumerate(["Bangkok", "Chiang Mai", "Khon Kaen"], start=1):
            province_id = cls._uuid()
            province_code = f"P{province_index:02d}"
            cls.areas["provinces"][province_id] = {
                "id": province_id,
                "region": f"Region {((province_index - 1) % 4) + 1}",
                "zone": f"Zone {((province_index - 1) % 3) + 1}",
                "provinceName": province_name,
                "provinceCode": province_code,
                "quota": 0,
            }
            for district_index in range(1, 3):
                district_id = cls._uuid()
                district_code = f"D{province_index:02d}{district_index:02d}"
                district_name = f"{province_name} District {district_index}"
                cls.areas["districts"][district_id] = {
                    "id": district_id,
                    "provinceId": province_id,
                    "districtName": district_name,
                    "districtCode": district_code,
                }
                for sub_index in range(1, 3):
                    sub_id = cls._uuid()
                    sub_code = f"S{province_index:02d}{district_index:02d}{sub_index:02d}"
                    sub_name = f"Subdistrict {sub_index}"
                    cls.areas["subdistricts"][sub_id] = {
                        "id": sub_id,
                        "provinceId": province_id,
                        "districtId": district_id,
                        "subdistrictName": sub_name,
                        "subdistrictCode": sub_code,
                    }
                    for village_index in range(1, 3):
                        village_id = cls._uuid()
                        village_code = f"V{province_index:02d}{district_index:02d}{sub_index:02d}{village_index:02d}"
                        village_name = f"Village {village_index}"
                        cls.areas["villages"][village_id] = {
                            "id": village_id,
                            "provinceId": province_id,
                            "districtId": district_id,
                            "subdistrictId": sub_id,
                            "villageName": village_name,
                            "villageCode": village_code,
                        }
                        community_id = cls._uuid()
                        cls.areas["communities"][community_id] = {
                            "id": community_id,
                            "provinceId": province_id,
                            "districtId": district_id,
                            "subdistrictId": sub_id,
                            "villageId": village_id,
                            "communityType": random.choice(["Urban", "Rural"]),
                            "communityName": f"Community {village_index}",
                            "communityCode": f"C{province_index:02d}{district_index:02d}{sub_index:02d}{village_index:02d}",
                        }

    @classmethod
    def _seed_groups_and_menus(cls) -> None:
        for name in ["Administrators", "Provincial Officers", "District Supervisors"]:
            group_id = cls._uuid()
            cls.groups[group_id] = {
                "id": group_id,
                "groupName": name,
                "description": f"Mock group for {name.lower()}",
            }

        for order, menu_name in enumerate(["Dashboard", "Volunteers", "Announcements", "Reports"], start=1):
            menu_id = cls._uuid()
            cls.main_menus[menu_id] = {
                "id": menu_id,
                "menuName": menu_name,
                "slug": menu_name.lower(),
                "order": order,
                "icon": ["bar-chart", "users", "bell", "file-text"][order - 1],
            }
            for sub_order, sub_name in enumerate(["List", "Create"], start=1):
                sub_id = cls._uuid()
                cls.sub_menus[sub_id] = {
                    "id": sub_id,
                    "mainMenuId": menu_id,
                    "mainMenu": menu_name,
                    "subMenu": f"{menu_name} {sub_name}",
                    "route": f"/{menu_name.lower()}/{sub_name.lower()}",
                    "order": sub_order,
                    "user": "system",
                }
                cls.menu_assignees.setdefault(sub_id, set()).add("admin")

    @classmethod
    def _seed_roles(cls) -> None:
        for role_name in ["admin", "manager", "viewer"]:
            role_id = cls._uuid()
            cls.roles[role_id] = {
                "id": role_id,
                "roleName": role_name,
            }
            cls.role_permissions[role_id] = {
                "manage_volunteers": role_name in {"admin", "manager"},
                "view_reports": True,
                "manage_announcements": role_name == "admin",
                "manage_users": role_name == "admin",
            }

    @classmethod
    def _seed_users(cls) -> None:
        admin_id = cls._uuid()
        cls.users[admin_id] = {
            "id": admin_id,
            "groupId": next(iter(cls.groups)),
            "groupName": "Administrators",
            "userCode": "ADM001",
            "username": "admin",
            "password": "password123",
            "firstName": "Arthit",
            "lastName": "Suwan",
            "email": "admin@example.com",
            "phone": "0800000000",
            "status": "active",
            "user_type": "officer",
            "scopes": ["profile", "admin"],
        }
        officer_id = cls._uuid()
        cls.users[officer_id] = {
            "id": officer_id,
            "groupId": next(iter(cls.groups)),
            "groupName": "Administrators",
            "userCode": "OFF001",
            "username": "officer",
            "password": "password123",
            "firstName": "Nok",
            "lastName": "Chan",
            "email": "officer@example.com",
            "phone": "0890000000",
            "status": "active",
            "user_type": "officer",
            "scopes": ["profile"],
        }

    @classmethod
    def _seed_volunteers(cls) -> None:
        training_catalog = [item["label"] for item in cls.meta_options.get("training-courses", [])]
        status_choices = ["active", "inactive", "pending"]
        for idx in range(1, 16):
            volunteer_id = cls._uuid()
            province = random.choice(list(cls.areas["provinces"].values()))
            district = random.choice([d for d in cls.areas["districts"].values() if d["provinceId"] == province["id"]])
            subdistrict = random.choice([
                s
                for s in cls.areas["subdistricts"].values()
                if s["provinceId"] == province["id"] and s["districtId"] == district["id"]
            ])
            volunteer = {
                "id": volunteer_id,
                "firstName": f"Volunteer {idx}",
                "lastName": "Mockdata",
                "status": random.choice(status_choices),
                "hospitalCode": f"H{idx:03d}",
                "province": {
                    "id": province["id"],
                    "name": province["provinceName"],
                    "code": province["provinceCode"],
                },
                "district": {
                    "id": district["id"],
                    "name": district["districtName"],
                    "code": district["districtCode"],
                },
                "subDistrict": {
                    "id": subdistrict["id"],
                    "name": subdistrict["subdistrictName"],
                    "code": subdistrict["subdistrictCode"],
                },
                "personal": {
                    "prefix": random.choice(cls.meta_options["prefixes"])["value"],
                    "gender": random.choice(["Male", "Female"]),
                    "birthDate": (datetime.utcnow() - timedelta(days=random.randint(25 * 365, 60 * 365))).date().isoformat(),
                    "citizenId": f"11037000{idx:04d}",
                    "phone": f"08{random.randint(10000000, 99999999)}",
                    "email": f"volunteer{idx}@example.com",
                },
                "address": {
                    "houseNumber": str(random.randint(10, 200)),
                    "village": random.choice(["Village 1", "Village 5", "Village 9"]),
                    "postalCode": "10330",
                },
                "spouse": {
                    "name": f"Spouse {idx}",
                    "occupation": random.choice(cls.meta_options["occupations"])["label"],
                },
                "children": [
                    {
                        "name": f"Child {idx}-{child}",
                        "age": random.randint(5, 20),
                    }
                    for child in range(random.randint(0, 3))
                ],
                "training": {
                    "selectedCourseIds": random.sample(training_catalog, k=min(2, len(training_catalog))),
                    "lastTrainingAt": (datetime.utcnow() - timedelta(days=random.randint(30, 365))).date().isoformat(),
                },
                "outstanding": {
                    "selectStatus": random.choice(["yes", "no"]),
                    "levelSelects": random.choice(["gold", "silver", "bronze"]),
                    "awardYear": datetime.utcnow().year,
                    "sectors": random.sample(["Community", "Health", "Education"], k=2),
                },
                "activityPhotos": [],
                "createdAt": datetime.utcnow().isoformat(),
                "updatedAt": datetime.utcnow().isoformat(),
            }
            cls.volunteers[volunteer_id] = volunteer
            cls.volunteer_history[volunteer_id] = [
                {
                    "timestamp": (datetime.utcnow() - timedelta(days=delta)).isoformat(),
                    "action": random.choice(["created", "updated training", "awarded"]),
                    "by": random.choice(["admin", "officer"]),
                }
                for delta in range(1, 4)
            ]

    @classmethod
    def _seed_announcements(cls) -> None:
        for idx, title in enumerate([
            "System maintenance",
            "New training available",
            "Volunteer meetup",
        ], start=1):
            announce_id = cls._uuid()
            cls.announcements[announce_id] = {
                "id": announce_id,
                "title": title,
                "date": (datetime.utcnow() - timedelta(days=idx)).date().isoformat(),
                "department": random.choice(["DOH", "Health Ministry", "Community"],),
                "body": f"Details for {title}",
            }
            cls.announcement_reads[announce_id] = set()

    @classmethod
    def _seed_reports(cls) -> None:
        current_year = datetime.utcnow().year
        cls.reports = {
            "volunteer-gender": [
                {
                    "districtCode": volunteer["district"]["code"],
                    "districtName": volunteer["district"]["name"],
                    "provinceName": volunteer["province"]["name"],
                    "total": random.randint(100, 400),
                    "male": random.randint(40, 200),
                    "female": random.randint(40, 200),
                }
                for volunteer in list(cls.volunteers.values())[:10]
            ],
            "volunteer-address": [
                {
                    "citizenId": volunteer["personal"]["citizenId"],
                    "name": f"{volunteer['firstName']} {volunteer['lastName']}",
                    "province": volunteer["province"]["name"],
                    "district": volunteer["district"]["name"],
                    "address": volunteer["address"]["village"],
                }
                for volunteer in cls.volunteers.values()
            ],
            "president-list": [
                {
                    "area": volunteer["province"]["name"],
                    "leader": f"{volunteer['firstName']} {volunteer['lastName']}",
                    "position": random.choice(["President", "Vice President"]),
                }
                for volunteer in list(cls.volunteers.values())[:8]
            ],
            "resigned-volunteers": [
                {
                    "name": f"{volunteer['firstName']} {volunteer['lastName']}",
                    "reason": random.choice(["Health", "Relocation"]),
                    "date": (datetime.utcnow() - timedelta(days=random.randint(10, 300))).date().isoformat(),
                }
                for volunteer in list(cls.volunteers.values())[:5]
            ],
            "benefit-claim": [
                {
                    "name": f"{volunteer['firstName']} {volunteer['lastName']}",
                    "claimStatus": random.choice(["approved", "pending", "rejected"]),
                }
                for volunteer in list(cls.volunteers.values())[:12]
            ],
            "new-volunteers": [
                {
                    "year": current_year - i,
                    "count": random.randint(20, 120),
                }
                for i in range(5)
            ],
            "volunteer-tenure": [
                {
                    "name": f"{volunteer['firstName']} {volunteer['lastName']}",
                    "tenureYears": random.randint(1, 20),
                }
                for volunteer in list(cls.volunteers.values())[:12]
            ],
            "average-age": [
                {
                    "area": volunteer["district"]["name"],
                    "averageAge": random.randint(30, 58),
                }
                for volunteer in list(cls.volunteers.values())[:10]
            ],
            "qualified-benefit": [
                {
                    "name": f"{volunteer['firstName']} {volunteer['lastName']}",
                    "eligible": random.choice([True, False]),
                }
                for volunteer in list(cls.volunteers.values())[:14]
            ],
            "vaccine-levels": [
                {
                    "area": volunteer["province"]["name"],
                    "vaccine": random.choice(["COVID-19", "Flu"]),
                    "coverage": random.randint(60, 100),
                }
                for volunteer in list(cls.volunteers.values())[:9]
            ],
            "specialty-by-area": [
                {
                    "area": volunteer["district"]["name"],
                    "specialty": random.choice(["Nutrition", "First Aid"]),
                    "count": random.randint(5, 45),
                }
                for volunteer in list(cls.volunteers.values())[:9]
            ],
            "positions-by-village": [
                {
                    "village": volunteer["address"]["village"],
                    "position": random.choice(["President", "Treasurer", "Member"]),
                    "allowanceEligible": random.choice([True, False]),
                }
                for volunteer in list(cls.volunteers.values())[:9]
            ],
            "president-by-level": [
                {
                    "level": level,
                    "count": random.randint(3, 12),
                }
                for level in ["Province", "District", "Subdistrict"]
            ],
            "training-by-area": [
                {
                    "area": volunteer["province"]["name"],
                    "coursesCompleted": len(volunteer["training"]["selectedCourseIds"]),
                }
                for volunteer in list(cls.volunteers.values())[:10]
            ],
            "tracking-by-level": [
                {
                    "level": level,
                    "progress": random.randint(50, 100),
                }
                for level in ["Province", "District", "Subdistrict", "Village"]
            ],
            "resigned-summary": [
                {
                    "province": volunteer["province"]["name"],
                    "totalResigned": random.randint(1, 20),
                }
                for volunteer in list(cls.volunteers.values())[:6]
            ],
        }

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _uuid() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def _to_options(values: List[str]) -> List[Dict[str, str]]:
        return [{"label": value, "value": value} for value in values]

    @staticmethod
    def _paginate(items: List[Dict[str, Any]], page: int, page_size: int) -> Tuple[List[Dict[str, Any]], int]:
        total = len(items)
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 10
        start = (page - 1) * page_size
        end = start + page_size
        return items[start:end], total

    @staticmethod
    def _response_envelope(
        items: List[Dict[str, Any]],
        total: int,
        page: int,
        page_size: int,
        message: str = "Success",
    ) -> Dict[str, Any]:
        return {
            "success": True,
            "message": message,
            "items": items,
            "total": total,
            "page": page,
            "pageSize": page_size,
        }

    @staticmethod
    def _single_response(data: Dict[str, Any], message: str = "Success") -> Dict[str, Any]:
        return {
            "success": True,
            "message": message,
            "data": data,
        }

    @staticmethod
    def _error(message: str, status_code: int = 400) -> Dict[str, Any]:
        return {
            "success": False,
            "message": message,
            "status_code": status_code,
        }

    # ------------------------------------------------------------------
    # User helpers
    # ------------------------------------------------------------------
    @classmethod
    def find_user_by_username(cls, username: str) -> Optional[Dict[str, Any]]:
        cls.ensure_initialized()
        for user in cls.users.values():
            if user["username"].lower() == username.lower():
                return deepcopy(user)
        return None

    @classmethod
    def find_user_by_id(cls, user_id: str) -> Optional[Dict[str, Any]]:
        cls.ensure_initialized()
        if user_id in cls.users:
            return deepcopy(cls.users[user_id])
        return None

    @classmethod
    def list_users(cls, page: int, page_size: int) -> Dict[str, Any]:
        cls.ensure_initialized()
        users = [deepcopy(user) for user in cls.users.values()]
        page_items, total = cls._paginate(users, page, page_size)
        return cls._response_envelope(page_items, total, page, page_size)

    @classmethod
    def create_user(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        cls.ensure_initialized()
        new_id = cls._uuid()
        user = {
            "id": new_id,
            "groupId": payload.get("groupId") or next(iter(cls.groups)),
            "groupName": payload.get("groupName") or "Administrators",
            "userCode": payload.get("userCode") or f"USR{len(cls.users) + 1:03d}",
            "username": payload["username"],
            "password": payload.get("password", "password123"),
            "firstName": payload.get("firstName", ""),
            "lastName": payload.get("lastName", ""),
            "email": payload.get("email"),
            "phone": payload.get("phone"),
            "status": payload.get("status", "active"),
            "user_type": payload.get("user_type", "officer"),
            "scopes": payload.get("scopes", ["profile"]),
        }
        cls.users[new_id] = user
        return cls._single_response(deepcopy(user), "User created")

    @classmethod
    def update_user(cls, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        cls.ensure_initialized()
        if user_id not in cls.users:
            return cls._error("User not found", 404)
        cls.users[user_id].update({k: v for k, v in payload.items() if v is not None})
        return cls._single_response(deepcopy(cls.users[user_id]), "User updated")

    @classmethod
    def delete_user(cls, user_id: str) -> Dict[str, Any]:
        cls.ensure_initialized()
        if user_id not in cls.users:
            return cls._error("User not found", 404)
        cls.users.pop(user_id)
        return cls._single_response({"id": user_id}, "User deleted")

    # ------------------------------------------------------------------
    # Group & menu helpers
    # ------------------------------------------------------------------
    @classmethod
    def list_groups(cls) -> List[Dict[str, Any]]:
        cls.ensure_initialized()
        return [deepcopy(group) for group in cls.groups.values()]

    @classmethod
    def create_group(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        cls.ensure_initialized()
        group_id = cls._uuid()
        cls.groups[group_id] = {
            "id": group_id,
            "groupName": payload.get("groupName", "Unnamed group"),
            "description": payload.get("description"),
        }
        return cls._single_response(deepcopy(cls.groups[group_id]), "Group created")

    @classmethod
    def update_group(cls, group_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        cls.ensure_initialized()
        if group_id not in cls.groups:
            return cls._error("Group not found", 404)
        cls.groups[group_id].update({k: v for k, v in payload.items() if v is not None})
        return cls._single_response(deepcopy(cls.groups[group_id]), "Group updated")

    @classmethod
    def delete_group(cls, group_id: str) -> Dict[str, Any]:
        cls.ensure_initialized()
        if group_id not in cls.groups:
            return cls._error("Group not found", 404)
        cls.groups.pop(group_id)
        return cls._single_response({"id": group_id}, "Group deleted")

    @classmethod
    def list_main_menus(cls) -> List[Dict[str, Any]]:
        cls.ensure_initialized()
        return [deepcopy(menu) for menu in cls.main_menus.values()]

    @classmethod
    def create_main_menu(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        cls.ensure_initialized()
        menu_id = cls._uuid()
        cls.main_menus[menu_id] = {
            "id": menu_id,
            "menuName": payload.get("menuName", "Untitled"),
            "slug": payload.get("slug", payload.get("menuName", "menu").lower()),
            "order": payload.get("order", len(cls.main_menus) + 1),
            "icon": payload.get("icon"),
        }
        return cls._single_response(deepcopy(cls.main_menus[menu_id]), "Main menu created")

    @classmethod
    def update_main_menu(cls, menu_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        cls.ensure_initialized()
        if menu_id not in cls.main_menus:
            return cls._error("Main menu not found", 404)
        cls.main_menus[menu_id].update({k: v for k, v in payload.items() if v is not None})
        return cls._single_response(deepcopy(cls.main_menus[menu_id]), "Main menu updated")

    @classmethod
    def delete_main_menu(cls, menu_id: str) -> Dict[str, Any]:
        cls.ensure_initialized()
        if menu_id not in cls.main_menus:
            return cls._error("Main menu not found", 404)
        cls.main_menus.pop(menu_id)
        return cls._single_response({"id": menu_id}, "Main menu deleted")

    @classmethod
    def list_sub_menus(cls, main_menu_id: Optional[str] = None) -> List[Dict[str, Any]]:
        cls.ensure_initialized()
        items = [deepcopy(menu) for menu in cls.sub_menus.values()]
        if main_menu_id:
            items = [item for item in items if item.get("mainMenuId") == main_menu_id]
        return items

    @classmethod
    def create_sub_menu(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        cls.ensure_initialized()
        sub_id = cls._uuid()
        cls.sub_menus[sub_id] = {
            "id": sub_id,
            "mainMenuId": payload.get("mainMenuId"),
            "mainMenu": payload.get("mainMenu"),
            "subMenu": payload.get("subMenu"),
            "route": payload.get("route"),
            "order": payload.get("order", len(cls.sub_menus) + 1),
            "user": payload.get("user", "system"),
        }
        return cls._single_response(deepcopy(cls.sub_menus[sub_id]), "Sub menu created")

    @classmethod
    def update_sub_menu(cls, sub_menu_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        cls.ensure_initialized()
        if sub_menu_id not in cls.sub_menus:
            return cls._error("Sub menu not found", 404)
        cls.sub_menus[sub_menu_id].update({k: v for k, v in payload.items() if v is not None})
        return cls._single_response(deepcopy(cls.sub_menus[sub_menu_id]), "Sub menu updated")

    @classmethod
    def delete_sub_menu(cls, sub_menu_id: str) -> Dict[str, Any]:
        cls.ensure_initialized()
        if sub_menu_id not in cls.sub_menus:
            return cls._error("Sub menu not found", 404)
        cls.sub_menus.pop(sub_menu_id)
        return cls._single_response({"id": sub_menu_id}, "Sub menu deleted")

    @classmethod
    def list_menu_assignees(cls, menu_id: str) -> List[Dict[str, Any]]:
        cls.ensure_initialized()
        usernames = cls.menu_assignees.get(menu_id, set())
        return [
            {
                "id": f"{menu_id}-{username}",
                "menuId": menu_id,
                "menuName": cls.sub_menus.get(menu_id, {}).get("subMenu"),
                "username": username,
            }
            for username in usernames
        ]

    @classmethod
    def add_menu_assignee(cls, menu_id: str, username: str) -> Dict[str, Any]:
        cls.ensure_initialized()
        cls.menu_assignees.setdefault(menu_id, set()).add(username)
        return cls._single_response({"menuId": menu_id, "username": username}, "Assignee added")

    @classmethod
    def remove_menu_assignee(cls, menu_id: str, username: str) -> Dict[str, Any]:
        cls.ensure_initialized()
        cls.menu_assignees.setdefault(menu_id, set()).discard(username)
        return cls._single_response({"menuId": menu_id, "username": username}, "Assignee removed")

    # ------------------------------------------------------------------
    # Roles & permissions
    # ------------------------------------------------------------------
    @classmethod
    def list_roles(cls) -> List[Dict[str, Any]]:
        cls.ensure_initialized()
        return [deepcopy(role) for role in cls.roles.values()]

    @classmethod
    def get_role_permissions(cls, role_id: str) -> Dict[str, Any]:
        cls.ensure_initialized()
        if role_id not in cls.roles:
            return cls._error("Role not found", 404)
        permissions = [
            {"key": key, "allowed": allowed}
            for key, allowed in cls.role_permissions.get(role_id, {}).items()
        ]
        return cls._single_response({"roleId": role_id, "permissions": permissions})

    @classmethod
    def update_role_permissions(cls, role_id: str, permissions: List[Dict[str, Any]]) -> Dict[str, Any]:
        cls.ensure_initialized()
        if role_id not in cls.roles:
            return cls._error("Role not found", 404)
        cls.role_permissions[role_id] = {perm["key"]: perm.get("allowed", False) for perm in permissions}
        return cls._single_response({"roleId": role_id, "permissions": permissions}, "Permissions updated")

    # ------------------------------------------------------------------
    # Volunteer helpers
    # ------------------------------------------------------------------
    @classmethod
    def list_volunteers(
        cls,
        filters: Dict[str, Optional[str]],
        page: int,
        page_size: int,
    ) -> Dict[str, Any]:
        cls.ensure_initialized()
        items = []
        for volunteer in cls.volunteers.values():
            if filters.get("firstName") and filters["firstName"].lower() not in volunteer["firstName"].lower():
                continue
            if filters.get("lastName") and filters["lastName"].lower() not in volunteer["lastName"].lower():
                continue
            if filters.get("status") and filters["status"].lower() != volunteer["status"].lower():
                continue
            if filters.get("hospitalCode") and filters["hospitalCode"].lower() not in volunteer["hospitalCode"].lower():
                continue
            if filters.get("province") and filters["province"] != volunteer["province"]["id"]:
                continue
            if filters.get("provinceCode") and filters["provinceCode"].lower() not in volunteer["province"]["code"].lower():
                continue
            if filters.get("district") and filters["district"] != volunteer["district"]["id"]:
                continue
            if filters.get("subDistrict") and filters["subDistrict"] != volunteer["subDistrict"]["id"]:
                continue
            items.append(deepcopy(volunteer))
        page_items, total = cls._paginate(items, page, page_size)
        return cls._response_envelope(page_items, total, page, page_size)

    @classmethod
    def get_volunteer(cls, volunteer_id: str) -> Optional[Dict[str, Any]]:
        cls.ensure_initialized()
        volunteer = cls.volunteers.get(volunteer_id)
        if volunteer:
            return deepcopy(volunteer)
        return None

    @classmethod
    def create_volunteer(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        cls.ensure_initialized()
        volunteer_id = cls._uuid()
        payload.setdefault("id", volunteer_id)
        payload.setdefault("status", "active")
        payload.setdefault("activityPhotos", [])
        payload.setdefault("createdAt", datetime.utcnow().isoformat())
        payload.setdefault("updatedAt", datetime.utcnow().isoformat())
        cls.volunteers[volunteer_id] = payload
        cls.volunteer_history[volunteer_id] = [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "action": "created",
                "by": "system",
            }
        ]
        return cls._single_response(deepcopy(payload), "Volunteer created")

    @classmethod
    def update_volunteer(cls, volunteer_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        cls.ensure_initialized()
        if volunteer_id not in cls.volunteers:
            return cls._error("Volunteer not found", 404)
        payload["updatedAt"] = datetime.utcnow().isoformat()
        cls.volunteers[volunteer_id] = {**cls.volunteers[volunteer_id], **payload}
        cls.volunteer_history.setdefault(volunteer_id, []).append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "action": "updated full record",
                "by": "system",
            }
        )
        return cls._single_response(deepcopy(cls.volunteers[volunteer_id]), "Volunteer updated")

    @classmethod
    def update_volunteer_section(cls, volunteer_id: str, section: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        cls.ensure_initialized()
        if volunteer_id not in cls.volunteers:
            return cls._error("Volunteer not found", 404)
        cls.volunteers[volunteer_id].setdefault(section, {})
        cls.volunteers[volunteer_id][section].update(payload)
        cls.volunteers[volunteer_id]["updatedAt"] = datetime.utcnow().isoformat()
        cls.volunteer_history.setdefault(volunteer_id, []).append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "action": f"updated {section}",
                "by": "system",
            }
        )
        return cls._single_response(deepcopy(cls.volunteers[volunteer_id]), f"Volunteer {section} updated")

    @classmethod
    def add_activity_photo(cls, volunteer_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        cls.ensure_initialized()
        if volunteer_id not in cls.volunteers:
            return cls._error("Volunteer not found", 404)
        cls.volunteers[volunteer_id].setdefault("activityPhotos", []).append(metadata)
        cls.volunteers[volunteer_id]["updatedAt"] = datetime.utcnow().isoformat()
        return cls._single_response(deepcopy(cls.volunteers[volunteer_id]["activityPhotos"]), "Photo uploaded")

    @classmethod
    def delete_volunteer(cls, volunteer_id: str) -> Dict[str, Any]:
        cls.ensure_initialized()
        if volunteer_id not in cls.volunteers:
            return cls._error("Volunteer not found", 404)
        cls.volunteers.pop(volunteer_id)
        cls.volunteer_history.pop(volunteer_id, None)
        return cls._single_response({"id": volunteer_id}, "Volunteer deleted")

    @classmethod
    def get_volunteer_history(cls, volunteer_id: str) -> List[Dict[str, Any]]:
        cls.ensure_initialized()
        history = cls.volunteer_history.get(volunteer_id, [])
        return [deepcopy(entry) for entry in history]

    # ------------------------------------------------------------------
    # Meta helpers
    # ------------------------------------------------------------------
    @classmethod
    def get_meta(cls, key: str) -> List[Dict[str, str]]:
        cls.ensure_initialized()
        return deepcopy(cls.meta_options.get(key, []))

    @classmethod
    def get_years(cls, start_type: str, count: int) -> List[Dict[str, str]]:
        cls.ensure_initialized()
        count = max(count, 1)
        current_year = datetime.utcnow().year
        if start_type == "be":
            current_year += 543
        years = [
            {"label": str(current_year - idx), "value": str(current_year - idx)}
            for idx in range(count)
        ]
        return years

    @classmethod
    def get_course_catalog(cls, year: int) -> Dict[str, Any]:
        cls.ensure_initialized()
        courses = [deepcopy(option) for option in cls.meta_options.get("training-courses", [])]
        for course in courses:
            course["year"] = year
            course["description"] = f"Course {course['label']} for year {year}"
        return {
            "items": courses,
            "year": year,
        }

    @classmethod
    def get_form_config(cls) -> Dict[str, Any]:
        cls.ensure_initialized()
        return {key: deepcopy(values) for key, values in cls.meta_options.items()}

    # ------------------------------------------------------------------
    # Area maintenance helpers
    # ------------------------------------------------------------------
    @classmethod
    def list_areas(
        cls,
        level: str,
        filters: Dict[str, Optional[str]],
        page: int,
        page_size: int,
    ) -> Dict[str, Any]:
        cls.ensure_initialized()
        items = []
        for area in cls.areas[level].values():
            matched = True
            keyword = filters.get("keyword")
            if keyword:
                matched = any(keyword.lower() in str(value).lower() for value in area.values())
            for key in ["provinceId", "districtId", "subdistrictId", "villageId"]:
                if filters.get(key) and area.get(key) != filters[key]:
                    matched = False
                    break
            if not matched:
                continue
            items.append(deepcopy(area))
        page_items, total = cls._paginate(items, page, page_size)
        return cls._response_envelope(page_items, total, page, page_size)

    @classmethod
    def create_area(cls, level: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        cls.ensure_initialized()
        area_id = cls._uuid()
        payload = {**payload, "id": area_id}
        cls.areas[level][area_id] = payload
        return cls._single_response(deepcopy(payload), f"{level[:-1].capitalize()} created")

    @classmethod
    def update_area(cls, level: str, area_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        cls.ensure_initialized()
        if area_id not in cls.areas[level]:
            return cls._error("Record not found", 404)
        cls.areas[level][area_id].update({k: v for k, v in payload.items() if v is not None})
        return cls._single_response(deepcopy(cls.areas[level][area_id]), f"{level[:-1].capitalize()} updated")

    @classmethod
    def delete_area(cls, level: str, area_id: str) -> Dict[str, Any]:
        cls.ensure_initialized()
        if area_id not in cls.areas[level]:
            return cls._error("Record not found", 404)
        cls.areas[level].pop(area_id)
        return cls._single_response({"id": area_id}, f"{level[:-1].capitalize()} deleted")

    # ------------------------------------------------------------------
    # Area info dashboards
    # ------------------------------------------------------------------
    @classmethod
    def get_area_info(cls, level: str, filters: Dict[str, Optional[str]], page: int, page_size: int) -> Dict[str, Any]:
        cls.ensure_initialized()
        filters = filters or {}
        results: List[Dict[str, Any]] = []
        year = filters.get("year") or str(datetime.utcnow().year + 543)
        search_value = filters.get("search")
        search = (search_value or "").lower()

        def matches_search(name: str) -> bool:
            return search in name.lower() if search else True

        if level == "provinces":
            for province in cls.areas["provinces"].values():
                if not matches_search(province["provinceName"]):
                    continue
                province_id = province["id"]
                districts = [d for d in cls.areas["districts"].values() if d["provinceId"] == province_id]
                volunteers = [v for v in cls.volunteers.values() if v["province"]["id"] == province_id]
                results.append(
                    {
                        "year": year,
                        "provinceCode": province["provinceCode"],
                        "provinceName": province["provinceName"],
                        "districtTotal": len(districts),
                        "pcuTotal": len(districts) * 2,
                        "hospitalTotal": len(districts) + 1,
                        "population": len(volunteers) * 120,
                        "volunteerTotal": len(volunteers),
                    }
                )
        elif level == "districts":
            province_filter = filters.get("province")
            for district in cls.areas["districts"].values():
                if province_filter and district["provinceId"] != province_filter:
                    continue
                if not matches_search(district["districtName"]):
                    continue
                volunteers = [v for v in cls.volunteers.values() if v["district"]["id"] == district["id"]]
                results.append(
                    {
                        "year": year,
                        "districtCode": district["districtCode"],
                        "districtName": district["districtName"],
                        "volunteerTotal": len(volunteers),
                        "facilityTotal": len(volunteers) // 2 + 1,
                        "population": len(volunteers) * 40,
                    }
                )
        elif level == "subdistricts":
            district_filter = filters.get("district")
            for subdistrict in cls.areas["subdistricts"].values():
                if district_filter and subdistrict["districtId"] != district_filter:
                    continue
                if not matches_search(subdistrict["subdistrictName"]):
                    continue
                volunteers = [v for v in cls.volunteers.values() if v["subDistrict"]["id"] == subdistrict["id"]]
                results.append(
                    {
                        "year": year,
                        "subdistrictCode": subdistrict["subdistrictCode"],
                        "subdistrictName": subdistrict["subdistrictName"],
                        "villageTotal": len(volunteers) // 3 + 1,
                        "population": len(volunteers) * 30,
                        "volunteerTotal": len(volunteers),
                    }
                )
        elif level == "villages":
            subdistrict_filter = filters.get("subdistrict")
            for village in cls.areas["villages"].values():
                if subdistrict_filter and village["subdistrictId"] != subdistrict_filter:
                    continue
                if not matches_search(village["villageName"]):
                    continue
                volunteers = [v for v in cls.volunteers.values() if v["address"]["village"] == village["villageName"]]
                results.append(
                    {
                        "year": year,
                        "villageCode": village["villageCode"],
                        "villageName": village["villageName"],
                        "population": len(volunteers) * 10,
                        "volunteerTotal": len(volunteers),
                    }
                )
        elif level == "communities":
            village_filter = filters.get("village")
            for community in cls.areas["communities"].values():
                if village_filter and community["villageId"] != village_filter:
                    continue
                if not matches_search(community["communityName"]):
                    continue
                volunteers = [
                    v
                    for v in cls.volunteers.values()
                    if v["address"].get("village", "") == cls.areas["villages"].get(community["villageId"], {}).get("villageName")
                ]
                results.append(
                    {
                        "year": year,
                        "communityCode": community["communityCode"],
                        "communityName": community["communityName"],
                        "volunteerTotal": len(volunteers),
                        "activityCount": len(volunteers) // 2 + 1,
                    }
                )
        page_items, total = cls._paginate(results, page, page_size)
        return cls._response_envelope(page_items, total, page, page_size)

    # ------------------------------------------------------------------
    # Announcements
    # ------------------------------------------------------------------
    @classmethod
    def list_announcements(cls, page: int, page_size: int, user_id: Optional[str]) -> Dict[str, Any]:
        cls.ensure_initialized()
        items = []
        for announce in cls.announcements.values():
            item = deepcopy(announce)
            reads = cls.announcement_reads.get(item["id"], set())
            item["isRead"] = user_id in reads if user_id else False
            items.append(item)
        items.sort(key=lambda x: x["date"], reverse=True)
        page_items, total = cls._paginate(items, page, page_size)
        return cls._response_envelope(page_items, total, page, page_size)

    @classmethod
    def mark_announcement_read(cls, announcement_id: str, user_id: str) -> Dict[str, Any]:
        cls.ensure_initialized()
        if announcement_id not in cls.announcements:
            return cls._error("Announcement not found", 404)
        cls.announcement_reads.setdefault(announcement_id, set()).add(user_id)
        return cls._single_response({"id": announcement_id}, "Marked as read")

    @classmethod
    def mark_all_announcements_read(cls, user_id: str) -> Dict[str, Any]:
        cls.ensure_initialized()
        for announcement_id in cls.announcements:
            cls.announcement_reads.setdefault(announcement_id, set()).add(user_id)
        return cls._single_response({"userId": user_id}, "All announcements marked as read")

    # ------------------------------------------------------------------
    # Reports
    # ------------------------------------------------------------------
    @classmethod
    def get_report(cls, key: str, filters: Dict[str, Optional[str]], page: int, page_size: int) -> Dict[str, Any]:
        cls.ensure_initialized()
        records = [deepcopy(item) for item in cls.reports.get(key, [])]
        province = filters.get("province")
        district = filters.get("district")
        year = filters.get("year")
        if province:
            records = [r for r in records if r.get("province") == province or r.get("provinceName") == province]
        if district:
            records = [r for r in records if r.get("district") == district or r.get("districtName") == district]
        if year:
            # Keep rows that either match year or don't include year filter
            filtered = []
            for record in records:
                record_year = record.get("year") or record.get("awardYear")
                if record_year is None or str(record_year) == str(year):
                    filtered.append(record)
            records = filtered
        page_items, total = cls._paginate(records, page, page_size)
        return cls._response_envelope(page_items, total, page, page_size)


MockDataStore.ensure_initialized()
