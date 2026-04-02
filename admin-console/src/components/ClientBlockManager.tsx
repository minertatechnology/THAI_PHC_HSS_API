import React, { useEffect, useMemo, useState } from "react";
import {
  ClientBlockCandidate,
  ClientBlockEntry,
  CreateClientBlockPayload,
  OAuthClientSummary,
  UserType,
} from "../types/oauthClient";
import {
  fetchClientBlocks,
  createClientBlock,
  deleteClientBlock,
  searchClientBlockCandidates,
  fetchClientAllows,
  createClientAllow,
  deleteClientAllow,
  updateOAuthClientAllowlistMode,
} from "../api/oauthClients";
import { SensitiveValue, EyeIcon, EyeOffIcon } from "./ui/SensitiveValue";

const USER_TYPE_LABEL: Record<UserType, string> = {
  officer: "Officer",
  osm: "OSM",
  yuwa_osm: "Yuwa OSM",
  people: "People",
  gen_h: "GenH",
};

const DEFAULT_USER_TYPE: UserType = "officer";

const formatDateTime = (value: string) => {
  try {
    return new Intl.DateTimeFormat("th-TH", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(value));
  } catch (_err) {
    return value;
  }
};

interface ClientBlockManagerProps {
  client: OAuthClientSummary;
  onClientUpdated?: (client: OAuthClientSummary) => void;
}

export const ClientBlockManager: React.FC<ClientBlockManagerProps> = ({
  client,
  onClientUpdated,
}) => {
  const [blocks, setBlocks] = useState<ClientBlockEntry[]>([]);
  const [loadingBlocks, setLoadingBlocks] = useState(true);
  const [blocksError, setBlocksError] = useState<string | null>(null);

  const [allowlistEnabled, setAllowlistEnabled] = useState<boolean>(
    Boolean(client.allowlist_enabled)
  );
  const [savingMode, setSavingMode] = useState(false);

  const [allows, setAllows] = useState<ClientBlockEntry[]>([] as any);
  const [loadingAllows, setLoadingAllows] = useState(true);
  const [allowsError, setAllowsError] = useState<string | null>(null);

  const [searchType, setSearchType] = useState<UserType>(DEFAULT_USER_TYPE);
  const [searchTerm, setSearchTerm] = useState("");
  const [searchResults, setSearchResults] = useState<ClientBlockCandidate[]>(
    []
  );
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  const [pendingBlockUserId, setPendingBlockUserId] = useState<string | null>(
    null
  );
  const [pendingDeleteBlockId, setPendingDeleteBlockId] = useState<
    string | null
  >(null);
  const [pendingAllowUserId, setPendingAllowUserId] = useState<string | null>(
    null
  );
  const [pendingDeleteAllowId, setPendingDeleteAllowId] = useState<
    string | null
  >(null);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    setAllowlistEnabled(Boolean(client.allowlist_enabled));
  }, [client.allowlist_enabled]);

  const loadBlocks = async () => {
    setLoadingBlocks(true);
    setBlocksError(null);
    try {
      const data = await fetchClientBlocks(client.client_id);
      setBlocks(data);
    } catch (err: any) {
      setBlocksError(
        err?.response?.data?.detail ??
          err?.message ??
          "ไม่สามารถโหลดรายการบล็อกได้"
      );
    } finally {
      setLoadingBlocks(false);
    }
  };

  const loadAllows = async () => {
    setLoadingAllows(true);
    setAllowsError(null);
    try {
      const data = await fetchClientAllows(client.client_id);
      setAllows(data as any);
    } catch (err: any) {
      setAllowsError(
        err?.response?.data?.detail ??
          err?.message ??
          "ไม่สามารถโหลดรายการที่อนุญาตได้"
      );
    } finally {
      setLoadingAllows(false);
    }
  };

  useEffect(() => {
    loadBlocks();
    loadAllows();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [client.client_id]);

  const [confirmMode, setConfirmMode] = useState<{
    show: boolean;
    nextEnabled: boolean;
  }>({ show: false, nextEnabled: false });

  const requestToggleMode = (nextEnabled: boolean) => {
    if (nextEnabled === allowlistEnabled) return;
    setConfirmMode({ show: true, nextEnabled });
  };

  const handleConfirmToggleMode = async () => {
    const nextEnabled = confirmMode.nextEnabled;
    setConfirmMode({ show: false, nextEnabled: false });
    setActionError(null);
    setSavingMode(true);
    try {
      const updated = await updateOAuthClientAllowlistMode(client.client_id, {
        allowlist_enabled: nextEnabled,
      });
      setAllowlistEnabled(Boolean(updated.allowlist_enabled));
      onClientUpdated?.(updated);
    } catch (err: any) {
      setActionError(
        err?.response?.data?.detail ??
          err?.message ??
          "ไม่สามารถอัปเดตโหมดการอนุญาตได้"
      );
    } finally {
      setSavingMode(false);
    }
  };

  const handleSearch = async (event: React.FormEvent) => {
    event.preventDefault();
    const term = searchTerm.trim();
    setSearchResults([]);
    setSearchError(null);
    setActionError(null);
    if (!term) {
      setSearchError("กรุณากรอกคำค้นหา");
      return;
    }
    setSearchLoading(true);
    try {
      const result = await searchClientBlockCandidates({
        userType: searchType,
        query: term,
        limit: 10,
      });
      setSearchResults(result.items);
      if (result.items.length === 0) {
        setSearchError("ไม่พบบัญชีที่ตรงกับคำค้นหา");
      }
    } catch (err: any) {
      setSearchError(
        err?.response?.data?.detail ??
          err?.message ??
          "เกิดข้อผิดพลาดในการค้นหา"
      );
    } finally {
      setSearchLoading(false);
    }
  };

  const handleBlock = async (candidate: ClientBlockCandidate) => {
    setActionError(null);
    setPendingBlockUserId(candidate.user_id);
    const payload: CreateClientBlockPayload = {
      user_id: candidate.user_id,
      user_type: candidate.user_type,
    };
    try {
      const entry = await createClientBlock(client.client_id, payload);
      setBlocks((prev) => [
        entry,
        ...prev.filter((item) => item.id !== entry.id),
      ]);
      setSearchResults((prev) =>
        prev.filter((item) => item.user_id !== candidate.user_id)
      );
    } catch (err: any) {
      setActionError(
        err?.response?.data?.detail ??
          err?.message ??
          "ไม่สามารถบล็อกผู้ใช้งานได้"
      );
    } finally {
      setPendingBlockUserId(null);
    }
  };

  const handleAllow = async (candidate: ClientBlockCandidate) => {
    setActionError(null);
    setPendingAllowUserId(candidate.user_id);
    const payload = {
      user_id: candidate.user_id,
      user_type: candidate.user_type,
    };
    try {
      const entry = await createClientAllow(client.client_id, payload);
      setAllows((prev: any[]) => [
        entry,
        ...prev.filter((item) => item.id !== entry.id),
      ]);
      setSearchResults((prev) =>
        prev.filter((item) => item.user_id !== candidate.user_id)
      );
    } catch (err: any) {
      setActionError(
        err?.response?.data?.detail ??
          err?.message ??
          "ไม่สามารถอนุญาตผู้ใช้งานได้"
      );
    } finally {
      setPendingAllowUserId(null);
    }
  };

  const handleUnblock = async (block: ClientBlockEntry) => {
    setActionError(null);
    setPendingDeleteBlockId(block.id);
    try {
      await deleteClientBlock(client.client_id, block.id);
      setBlocks((prev) => prev.filter((item) => item.id !== block.id));
    } catch (err: any) {
      setActionError(
        err?.response?.data?.detail ??
          err?.message ??
          "ไม่สามารถปลดบล็อกผู้ใช้งานได้"
      );
    } finally {
      setPendingDeleteBlockId(null);
    }
  };

  const handleUnallow = async (allow: any) => {
    setActionError(null);
    setPendingDeleteAllowId(allow.id);
    try {
      await deleteClientAllow(client.client_id, allow.id);
      setAllows((prev: any[]) => prev.filter((item) => item.id !== allow.id));
    } catch (err: any) {
      setActionError(
        err?.response?.data?.detail ??
          err?.message ??
          "ไม่สามารถลบผู้ใช้งานที่อนุญาตได้"
      );
    } finally {
      setPendingDeleteAllowId(null);
    }
  };

  const blockedUserIds = useMemo(
    () => new Set(blocks.map((entry) => entry.user_id)),
    [blocks]
  );
  const allowedUserIds = useMemo(
    () => new Set((allows as any[]).map((entry) => entry.user_id)),
    [allows]
  );

  const filteredSearchResults = useMemo(
    () =>
      searchResults.filter((candidate) => {
        if (allowlistEnabled) {
          return !allowedUserIds.has(candidate.user_id);
        }
        return !blockedUserIds.has(candidate.user_id);
      }),
    [searchResults, blockedUserIds, allowedUserIds, allowlistEnabled]
  );

  return (
    <div className="bg-slate-50 px-4 py-6 sm:px-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-baseline sm:justify-between">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">
            บล็อกผู้ใช้รายบุคคล
          </h3>
          <p className="text-sm text-slate-600">
            {allowlistEnabled
              ? `โหมด Allow: ทุกคนจะเข้า ${client.client_name} ไม่ได้ ยกเว้นรายชื่อที่อนุญาตเท่านั้น`
              : `เมื่อบล็อกแล้ว ผู้ใช้จะไม่สามารถล็อกอินเข้า ${client.client_name} ได้ แต่ยังเข้าระบบอื่นได้ตามปกติ`}
          </p>
        </div>
        <button
          type="button"
          className="text-sm text-blue-600 transition hover:text-blue-700"
          onClick={allowlistEnabled ? loadAllows : loadBlocks}
          disabled={allowlistEnabled ? loadingAllows : loadingBlocks}
        >
          รีเฟรชรายการ
        </button>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <button
          type="button"
          className={`rounded-full border px-3 py-1 text-xs font-semibold transition ${
            !allowlistEnabled
              ? "border-slate-200 bg-white text-slate-700"
              : "border-slate-200 text-slate-500 hover:bg-white"
          }`}
          onClick={() => requestToggleMode(false)}
          disabled={savingMode}
        >
          โหมด Block
        </button>
        <button
          type="button"
          className={`rounded-full border px-3 py-1 text-xs font-semibold transition ${
            allowlistEnabled
              ? "border-amber-200 bg-amber-50 text-amber-700"
              : "border-slate-200 text-slate-500 hover:bg-white"
          }`}
          onClick={() => requestToggleMode(true)}
          disabled={savingMode}
        >
          โหมด Allow
        </button>
        {savingMode && (
          <span className="text-xs text-slate-500">กำลังบันทึกโหมด...</span>
        )}
      </div>

      {confirmMode.show && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm">
          <div className="mx-4 w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
            <h3 className="text-lg font-semibold text-slate-900">
              {confirmMode.nextEnabled
                ? "ยืนยันเปลี่ยนเป็นโหมด Allow"
                : "ยืนยันเปลี่ยนเป็นโหมด Block"}
            </h3>
            <div className="mt-3 space-y-2 text-sm text-slate-600">
              {confirmMode.nextEnabled ? (
                <>
                  <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-rose-700 font-medium">
                    ผู้ใช้ทุกคนจะเข้าระบบ {client.client_name} ไม่ได้ทันที
                    ยกเว้นเฉพาะรายชื่อที่อยู่ใน Allow List เท่านั้น
                  </p>
                  <p>
                    หากยังไม่ได้เพิ่มรายชื่อใน Allow List จะไม่มีใครสามารถ Login
                    เข้าระบบนี้ได้เลย
                  </p>
                </>
              ) : (
                <>
                  <p className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-blue-700 font-medium">
                    ผู้ใช้ทุกคนจะสามารถเข้าระบบ {client.client_name} ได้ตามปกติ
                    ยกเว้นเฉพาะรายชื่อที่ถูกบล็อก
                  </p>
                </>
              )}
            </div>
            <div className="mt-5 flex justify-end gap-3">
              <button
                type="button"
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-100"
                onClick={() =>
                  setConfirmMode({ show: false, nextEnabled: false })
                }
              >
                ยกเลิก
              </button>
              <button
                type="button"
                className={`rounded-lg px-4 py-2 text-sm font-semibold text-white transition ${
                  confirmMode.nextEnabled
                    ? "bg-amber-600 hover:bg-amber-700"
                    : "bg-blue-600 hover:bg-blue-700"
                }`}
                onClick={handleConfirmToggleMode}
              >
                ยืนยันเปลี่ยนโหมด
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="mt-5 grid gap-6 lg:grid-cols-[1.3fr,1fr]">
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-200 px-5 py-4">
            <h4 className="text-sm font-semibold text-slate-800">
              {allowlistEnabled ? "รายชื่อที่อนุญาต" : "รายชื่อที่ถูกบล็อก"}
            </h4>
          </div>
          <div className="px-5 py-4">
            {allowlistEnabled ? (
              loadingAllows ? (
                <p className="text-sm text-slate-500">กำลังโหลด...</p>
              ) : allowsError ? (
                <p className="text-sm text-rose-600">{allowsError}</p>
              ) : (allows as any[]).length === 0 ? (
                <p className="text-sm text-slate-500">
                  ยังไม่มีรายชื่อที่อนุญาต
                </p>
              ) : (
                <div className="space-y-3">
                  {(allows as any[]).map((allow) => (
                    <div
                      key={allow.id}
                      className="flex flex-col gap-2 rounded-lg border border-slate-200 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
                    >
                      <div>
                        <div className="text-sm font-medium text-slate-900">
                          {allow.full_name ?? "ไม่ทราบชื่อ"}
                        </div>
                        <div className="text-xs text-slate-500">
                          {allow.citizen_id ? (
                            <span className="inline-flex flex-wrap items-center gap-2">
                              <span>เลขบัตรประชาชน</span>
                              <SensitiveValue
                                value={allow.citizen_id}
                                className="inline-flex items-center gap-1"
                                valueClassName="font-mono text-xs text-slate-600"
                                buttonClassName="rounded-full px-2 py-0.5 text-[10px]"
                                revealIcon={<EyeIcon />}
                                hideIcon={<EyeOffIcon />}
                              />
                            </span>
                          ) : (
                            "ไม่ระบุเลขบัตร"
                          )}
                        </div>
                        <div className="mt-1 text-xs text-slate-400">
                          {USER_TYPE_LABEL[allow.user_type as UserType]} · อนุญาตเมื่อ{" "}
                          {formatDateTime(allow.created_at)}
                        </div>
                      </div>
                      <button
                        type="button"
                        className="inline-flex items-center justify-center rounded-full border border-slate-200 px-3 py-1 text-xs font-medium text-slate-600 transition hover:border-slate-300 hover:bg-slate-100 hover:text-slate-900"
                        onClick={() => handleUnallow(allow)}
                        disabled={pendingDeleteAllowId === allow.id}
                      >
                        {pendingDeleteAllowId === allow.id
                          ? "กำลังลบ..."
                          : "เอาออก"}
                      </button>
                    </div>
                  ))}
                </div>
              )
            ) : loadingBlocks ? (
              <p className="text-sm text-slate-500">กำลังโหลด...</p>
            ) : blocksError ? (
              <p className="text-sm text-rose-600">{blocksError}</p>
            ) : blocks.length === 0 ? (
              <p className="text-sm text-slate-500">
                ยังไม่มีรายชื่อที่ถูกบล็อก
              </p>
            ) : (
              <div className="space-y-3">
                {blocks.map((block) => (
                  <div
                    key={block.id}
                    className="flex flex-col gap-2 rounded-lg border border-slate-200 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div>
                      <div className="text-sm font-medium text-slate-900">
                        {block.full_name ?? "ไม่ทราบชื่อ"}
                      </div>
                      <div className="text-xs text-slate-500">
                        {block.citizen_id ? (
                          <span className="inline-flex flex-wrap items-center gap-2">
                            <span>เลขบัตรประชาชน</span>
                            <SensitiveValue
                              value={block.citizen_id}
                              className="inline-flex items-center gap-1"
                              valueClassName="font-mono text-xs text-slate-600"
                              buttonClassName="rounded-full px-2 py-0.5 text-[10px]"
                              revealIcon={<EyeIcon />}
                              hideIcon={<EyeOffIcon />}
                            />
                          </span>
                        ) : (
                          "ไม่ระบุเลขบัตร"
                        )}
                      </div>
                      <div className="mt-1 text-xs text-slate-400">
                        {USER_TYPE_LABEL[block.user_type]} · บล็อกเมื่อ{" "}
                        {formatDateTime(block.created_at)}
                      </div>
                    </div>
                    <button
                      type="button"
                      className="inline-flex items-center justify-center rounded-full border border-slate-200 px-3 py-1 text-xs font-medium text-slate-600 transition hover:border-slate-300 hover:bg-slate-100 hover:text-slate-900"
                      onClick={() => handleUnblock(block)}
                      disabled={pendingDeleteBlockId === block.id}
                    >
                      {pendingDeleteBlockId === block.id
                        ? "กำลังปลดบล็อก..."
                        : "ปลดบล็อก"}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-200 px-5 py-4">
            <h4 className="text-sm font-semibold text-slate-800">
              {allowlistEnabled
                ? "ค้นหาเพื่ออนุญาตเพิ่ม"
                : "ค้นหาเพื่อบล็อกเพิ่ม"}
            </h4>
          </div>
          <div className="px-5 py-4">
            <form className="space-y-3" onSubmit={handleSearch}>
              <div className="grid gap-2">
                <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  ประเภทผู้ใช้
                </label>
                <select
                  className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                  value={searchType}
                  onChange={(event) =>
                    setSearchType(event.target.value as UserType)
                  }
                >
                  <option value="officer">Officer</option>
                  <option value="osm">OSM</option>
                  <option value="yuwa_osm">Yuwa OSM</option>
                  <option value="people">People</option>
                </select>
              </div>
              <div className="grid gap-2">
                <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  ค้นหาจากชื่อหรือเลขบัตรประชาชน
                </label>
                <input
                  value={searchTerm}
                  onChange={(event) => setSearchTerm(event.target.value)}
                  className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                  placeholder="เช่น 1103700xxxxxxx หรือ กัญญา"
                />
              </div>
              <button
                type="submit"
                className="w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-300"
                disabled={searchLoading}
              >
                {searchLoading ? "กำลังค้นหา..." : "ค้นหา"}
              </button>
            </form>

            {searchError && (
              <p className="mt-3 text-xs text-rose-600">{searchError}</p>
            )}

            {actionError && (
              <p className="mt-3 text-xs text-rose-600">{actionError}</p>
            )}

            <div className="mt-4 space-y-3">
              {filteredSearchResults.map((candidate) => (
                <div
                  key={`${candidate.user_type}-${candidate.user_id}`}
                  className="flex flex-col gap-2 rounded-lg border border-slate-200 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div>
                    <div className="text-sm font-medium text-slate-900">
                      {candidate.full_name}
                    </div>
                    <div className="text-xs text-slate-500">
                      {candidate.citizen_id ? (
                        <span className="inline-flex flex-wrap items-center gap-2">
                          <span>เลขบัตรประชาชน</span>
                          <SensitiveValue
                            value={candidate.citizen_id}
                            className="inline-flex items-center gap-1"
                            valueClassName="font-mono text-xs text-slate-600"
                            buttonClassName="rounded-full px-2 py-0.5 text-[10px]"
                            revealIcon={<EyeIcon />}
                            hideIcon={<EyeOffIcon />}
                          />
                        </span>
                      ) : (
                        "ไม่ระบุเลขบัตร"
                      )}
                    </div>
                    <div className="mt-1 text-xs text-slate-400">
                      ประเภท {USER_TYPE_LABEL[candidate.user_type]}
                    </div>
                    {candidate.user_type === "people" && (
                      <div className="mt-2 space-y-1 text-xs">
                        <div>
                          {candidate.is_transferred ? (
                            <span className="inline-flex items-center rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-700">
                              ย้ายแล้ว
                            </span>
                          ) : (
                            <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-600">
                              ยังไม่ย้าย
                            </span>
                          )}
                        </div>
                        {candidate.is_transferred && (
                          <div className="text-slate-500">
                            <div>
                              {candidate.yuwa_osm_code ? (
                                <span>รหัส Yuwa OSM: {candidate.yuwa_osm_code}</span>
                              ) : null}
                            </div>
                            <div>
                              {candidate.yuwa_osm_id
                                ? `Yuwa OSM ID: ${candidate.yuwa_osm_id}`
                                : null}
                            </div>
                            <div>
                              {candidate.transferred_at
                                ? `ย้ายเมื่อ ${formatDateTime(candidate.transferred_at)}`
                                : "ย้ายแล้ว (ไม่ระบุเวลา)"}
                            </div>
                            <div>
                              {candidate.transferred_by
                                ? `ผู้ทำรายการ: ${candidate.transferred_by}`
                                : null}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                  <button
                    type="button"
                    className={`inline-flex items-center justify-center rounded-full px-3 py-1 text-xs font-semibold text-white transition disabled:cursor-not-allowed ${
                      allowlistEnabled
                        ? "bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-300"
                        : "bg-rose-600 hover:bg-rose-700 disabled:bg-rose-300"
                    }`}
                    onClick={() =>
                      allowlistEnabled
                        ? handleAllow(candidate)
                        : handleBlock(candidate)
                    }
                    disabled={
                      allowlistEnabled
                        ? pendingAllowUserId === candidate.user_id
                        : pendingBlockUserId === candidate.user_id
                    }
                  >
                    {allowlistEnabled
                      ? pendingAllowUserId === candidate.user_id
                        ? "กำลังอนุญาต..."
                        : "อนุญาตผู้ใช้งาน"
                      : pendingBlockUserId === candidate.user_id
                      ? "กำลังบล็อก..."
                      : "บล็อกผู้ใช้งาน"}
                  </button>
                </div>
              ))}
            </div>

            {!searchLoading &&
              filteredSearchResults.length === 0 &&
              !searchError &&
              searchTerm.trim() && (
                <p className="mt-4 text-xs text-slate-500">
                  {allowlistEnabled
                    ? "ไม่มีผลลัพธ์ที่พร้อมให้อนุญาต"
                    : "ไม่มีผลลัพธ์ที่พร้อมให้บล็อก"}
                </p>
              )}
          </div>
        </div>
      </div>
    </div>
  );
};
