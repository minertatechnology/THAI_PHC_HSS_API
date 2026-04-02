import React, { useMemo, useState } from "react";
import QuickSearchPage from "./QuickSearchPage";
import { UserType } from "../types/oauthClient";

type CommunityUserType = Extract<UserType, "osm" | "yuwa_osm" | "people" | "gen_h">;

type CommunityOption = {
  value: CommunityUserType;
  label: string;
  description: string;
  placeholder: string;
  helperText: string;
};

const COMMUNITY_OPTIONS: CommunityOption[] = [
  {
    value: "osm",
    label: "ค้นหา อสม.",
    description: "ค้นหาข้อมูลอาสาสมัครสาธารณสุขประจำหมู่บ้าน (อสม.) เพื่อประสานงานหรือช่วยเหลือการใช้งานระบบ",
    placeholder: "พิมพ์ชื่อ นามสกุล หรือเลขบัตรประชาชน",
    helperText: "ผลลัพธ์จะแสดงเฉพาะบัญชีที่เปิดใช้งาน แสดงผลครั้งละ 50 รายการ"
  },
  {
    value: "yuwa_osm",
    label: "ค้นหา ยุวอสม.",
    description: "ค้นหาผู้ใช้งาน ยุวอสม. เพื่อสนับสนุนการใช้งานแพลตฟอร์มและจัดการข้อมูลผู้ใช้",
    placeholder: "พิมพ์ชื่อ เลขบัตรประชาชน หรือหมายเลขโทรศัพท์",
    helperText: "ข้อมูลที่แสดงเป็นบัญชีที่ใช้งานอยู่ แสดงผลครั้งละ 50 รายการ"
  },
  {
    value: "people",
    label: "ค้นหา ประชาชน",
    description: "ค้นหาผู้ใช้งานประชาชนเพื่อช่วยเหลือการใช้งานและจัดการบัญชี",
    placeholder: "พิมพ์ชื่อ นามสกุล หรือเลขบัตรประชาชน",
    helperText: "ผลลัพธ์จะแสดงเฉพาะบัญชีที่เปิดใช้งาน แสดงผลครั้งละ 50 รายการ"
  },
  {
    value: "gen_h",
    label: "ค้นหา GenH",
    description: "ค้นหาผู้ใช้งาน GenH เพื่อจัดการข้อมูลสมาชิกและช่วยเหลือการใช้งานระบบ",
    placeholder: "พิมพ์ชื่อ นามสกุล รหัสบัตรสมาชิก หรือหมายเลขโทรศัพท์",
    helperText: "ผลลัพธ์จะแสดงเฉพาะบัญชีที่เปิดใช้งาน แสดงผลครั้งละ 50 รายการ"
  }
];

const INTRO_HIGHLIGHTS = [
  { label: "ข้อมูลติดต่อ", detail: "แสดงหมายเลขโทรศัพท์และอีเมลเมื่อมีข้อมูล" },
  { label: "พื้นที่รับผิดชอบ", detail: "จังหวัด อำเภอ และตำบลที่สังกัดอยู่" },
  { label: "บทบาทและหน่วยงาน", detail: "แสดงหน่วยงานหรือองค์กร พร้อมบทบาทผู้ใช้งาน" }
];

const CommunityQuickSearchPage: React.FC = () => {
  const [activeValue, setActiveValue] = useState<CommunityUserType>(COMMUNITY_OPTIONS[0].value);

  const activeOption = useMemo(
    () => COMMUNITY_OPTIONS.find((option) => option.value === activeValue) ?? COMMUNITY_OPTIONS[0],
    [activeValue]
  );

  const headerActions = (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap gap-2">
        {COMMUNITY_OPTIONS.map((option) => {
          const isActive = option.value === activeValue;
          return (
            <button
              key={option.value}
              type="button"
              onClick={() => setActiveValue(option.value)}
              className={`rounded-full px-4 py-1.5 text-xs font-semibold transition ${
                isActive ? "bg-white text-emerald-600 shadow" : "bg-white/20 text-white/80 hover:bg-white/30"
              }`}
            >
              {option.label}
            </button>
          );
        })}
      </div>
      <p className="text-xs text-white/80">{activeOption.description}</p>
    </div>
  );

  return (
    <QuickSearchPage
      userType={activeOption.value}
      title="ค้นหาโปรไฟล์ผู้ใช้งาน"
      subtitle="รวมการค้นหา อสม. ยุวอสม. ประชาชน และ GenH ในหน้าจอเดียว"
      description="ค้นหาและดูข้อมูลติดต่อของผู้ใช้งานในพื้นที่ได้รวดเร็วขึ้น เพื่อการตอบสนองงานส่วนกลาง"
      placeholder={activeOption.placeholder}
      helperText={activeOption.helperText}
      headerActions={headerActions}
      introHighlights={INTRO_HIGHLIGHTS}
    />
  );
};

export default CommunityQuickSearchPage;
