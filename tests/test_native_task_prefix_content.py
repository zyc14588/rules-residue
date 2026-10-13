"""Execute the finite tutorial on an explicitly selected native Host source.

The generated test lives in an owned copy of the Host module. Its repository
adapter implements the real transaction interfaces; this is not a SQL or room
integration test. Codec wrappers use the actual implementation module and are
labelled separately from the unchanged archive entrypoint gameplay scenarios.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import unittest
from unittest import mock

from tests import test_native_task_prefix_contract as oracle

ROOT = oracle.ROOT
NATIVE_REPORT = None
TASK = "TASK.TEST.CLOCK_OBSERVATION.V1"
A, B = "opening-seat-A", "opening-seat-B"
TEXT = "显示牌变动后回到同一分钟。"


def digest(value):
    return "sha256:" + hashlib.sha256(value).hexdigest()


def lua_literal(value):
    if isinstance(value, str):
        return '"' + "".join("\\%03d" % b for b in value.encode("utf-8")) + '"'
    if isinstance(value, list):
        return "{" + ",".join(map(lua_literal, value)) + "}"
    if isinstance(value, dict):
        return "{" + ",".join("[" + lua_literal(k) + "]=" + lua_literal(v)
                               for k, v in value.items()) + "}"
    raise ValueError("unsupported codec test literal")


def host_inventory(host):
    run = subprocess.run(["git", "-C", str(host), "ls-files", "-z"],
                         capture_output=True, check=True)
    rows = []
    for raw in run.stdout.split(b"\0")[:-1]:
        name = os.fsdecode(raw)
        p = host / name
        if not p.is_file() or p.is_symlink():
            raise RuntimeError("native source contains a nonregular tracked input")
        rows.append((name, stat.S_IMODE(p.stat().st_mode), digest(p.read_bytes())))
    if not rows:
        raise RuntimeError("native source has no tracked inputs")
    return rows


def host_git_state(host):
    return {name: subprocess.check_output(["git", "-C", str(host), *arguments], text=True).strip()
            for name, arguments in {"commit": ["rev-parse", "HEAD"],
                                    "tree": ["rev-parse", "HEAD^{tree}"],
                                    "status": ["status", "--porcelain=v1", "--untracked-files=all"]}.items()}


def run_native():
    locator = os.environ.get("RR_LUA_HOST_REPOSITORY")
    if not locator:
        if os.environ.get("RR_NATIVE_RUNTIME_REQUIRED") == "1":
            raise RuntimeError("strict native qualification requires RR_LUA_HOST_REPOSITORY")
        raise unittest.SkipTest("no native Host locator; no game runtime qualification")
    host = Path(locator).resolve(strict=True)
    if not (host / "go.mod").is_file() or not shutil.which("go"):
        raise RuntimeError("native Host source or Go is unavailable")
    contract = oracle.read_json("contract.json")
    for path, expected in contract["native_consumer"]["source_files"].items():
        if not (path.endswith(".go") or path in ("go.mod", "go.sum")):
            continue
        if path.startswith(("internal/platform/launch/", "tests/integration/")):
            continue
        if hashlib.sha256((host / path).read_bytes()).hexdigest() != expected:
            raise RuntimeError("native source binding mismatch: " + path)
    before = host_inventory(host)
    git_before = host_git_state(host)
    fixture = oracle.read_json("fixtures/task-prefix-cases.json")
    schema_cases = [{"id": x["id"], "schema": x["schema"], "value": oracle.vector_value(x),
                     "valid": x["valid"]} for x in fixture["schema_vectors"]]
    codec_cases = []
    for x in fixture["payload_codec_vectors"]:
        source = ("local m=require('lua.task_prefix');local j,h=m.encode_payload(" +
                  lua_literal(x["payload"]) + ");return {payload_json=j,payload_sha256=h}")
        codec_cases.append({"id": x["id"], "source": source})
    request = {"root": str(ROOT), "schema_cases": schema_cases, "codec_cases": codec_cases,
               "budget_cases": [{"id": x["id"], "texts": [step["payload"]["text"] for step in x["steps"]]}
                                for x in fixture["native_budget_regression"]["cases"]]}
    evidence_root = os.environ.get("RR_NATIVE_EVIDENCE_DIRECTORY")
    evidence = Path(tempfile.mkdtemp(prefix="task-prefix-native-", dir=evidence_root)) if evidence_root else None
    try:
        with tempfile.TemporaryDirectory(prefix="task-prefix-native-build-") as directory:
            temporary = Path(directory)
            module = temporary / "host"
            module.mkdir()
            for name, _, _ in before:
                p = module / name
                p.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(host / name, p)
            generated = module / "internal/package/install/task_prefix_content_generated_test.go"
            generated.write_text(GO_HARNESS, encoding="utf-8")
            spec, result = temporary / "request.json", temporary / "report.json"
            spec.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
            env = dict(os.environ, RR_GAME_SPEC=str(spec), RR_GAME_REPORT=str(result),
                       GOCACHE=os.environ.get("RR_NATIVE_GO_CACHE", str(temporary / "go-cache")),
                       GOPROXY="off", GOSUMDB="off",
                       GOFLAGS=(os.environ.get("GOFLAGS", "") + " -buildvcs=false").strip())
            command = ["go", "test", "./internal/package/install", "-run", "^TestNativeTaskPrefixContent$",
                       "-count=1", "-timeout=180s", "-v"]
            completed = subprocess.run(command, cwd=module, env=env, capture_output=True,
                                       text=True, timeout=240)
            metadata = {"command": command, "exit": completed.returncode,
                        "harness_sha256": digest(GO_HARNESS.encode()),
                        "source_inventory_sha256": digest(json.dumps(before).encode()),
                        "host_commit": git_before["commit"], "host_tree": git_before["tree"],
                        "host_status": git_before["status"],
                        "test_source_sha256": digest(Path(__file__).read_bytes()),
                        "source": {p: digest((ROOT / p).read_bytes()) for p in
                                   ["lua/main.lua", "lua/task_prefix.lua", "manifest.yaml"]}}
            if evidence:
                (evidence / "harness.go").write_text(GO_HARNESS)
                (evidence / "request.json").write_text(spec.read_text())
                (evidence / "stdout.txt").write_text(completed.stdout)
                (evidence / "stderr.txt").write_text(completed.stderr)
                (evidence / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
                if result.exists(): shutil.copy2(result, evidence / "report.json")
            if completed.returncode:
                raise RuntimeError("native harness failed; exit=" + str(completed.returncode) +
                                   ("; evidence=" + str(evidence) if evidence else ""))
            report = json.loads(result.read_text())
            report["binding"] = metadata
            if report.get("complete") is not True:
                raise RuntimeError("native harness returned an incomplete report")
            return report
    finally:
        if host_inventory(host) != before or host_git_state(host) != git_before:
            raise RuntimeError("native source changed during test execution")


def normalized_state(actual, expected):
    """Map predicted fixture IDs only after native provenance was checked."""
    mapping = {k: "evt-%032x" % (v["sequence"] + 1) for k, v in actual["events"].items()}
    for seat, row in actual["ledger"]["seats"].items():
        if row["settlement_receipt_id"]:
            mapping[row["settlement_receipt_id"]] = expected["ledger"]["seats"][seat]["settlement_receipt_id"]
    def walk(value):
        if isinstance(value, str): return mapping.get(value, value)
        if isinstance(value, list): return [walk(x) for x in value]
        if isinstance(value, dict): return {mapping.get(k, k): walk(v) for k, v in value.items()}
        return value
    result = walk(actual)
    for binding in result["execution_bindings"].values():
        if binding.get("callback") == "on_session_end": continue
        payload = walk(json.loads(binding["payload_json"]))
        binding["payload_json"] = oracle.canonical_payload_json(payload)
        binding["payload_sha256"] = digest(binding["payload_json"].encode())
    return result


class NativeTaskPrefixContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global NATIVE_REPORT
        cls.report = NATIVE_REPORT = run_native()
        cls.fixture = oracle.read_json("fixtures/task-prefix-cases.json")
        cls.validators = oracle.validators()

    def test_native_archive_callbacks_and_exact_fixture_flow(self):
        r = self.report
        self.assertEqual(set(r["callbacks"]), set(oracle.CALLBACKS))
        self.assertTrue(r["archive_hash"].startswith("sha256:"))
        self.assertEqual(len(r["main"]["steps"]), 14)
        actual = r["main"]["final"]
        expected = copy.deepcopy(self.fixture["states"]["final"])
        normalized = normalized_state(actual, expected)
        # Private notes in the snapshot vectors are separately provisioned test
        # material; no note-writing action is part of this finite command set.
        for state in (expected, normalized):
            for row in state["ledger"]["seats"].values(): row["private_notes"] = []
        self.assertTrue(normalized == expected, "native flow differs from exact independent fixture")
        self.assertEqual(len(r["main"]["events"]), 15)
        self.assertTrue(all(x["passed"] for x in r["hostcase_negatives"]))
        self.assertEqual(len(r["hostcase_negatives"]), 4)
        self.assertEqual(len(r["schema_cases"]), len(self.fixture["schema_vectors"]))
        self.assertTrue(all(x["passed"] for x in r["schema_cases"]))
        self.assertEqual(len(r["callback_results"]), 11)
        self.assertTrue(all(x["exact_expected_result"] for x in r["callback_results"]))

    def test_observed_transactions_provenance_and_read_only_projections(self):
        for scenario in self.report["scenarios"]:
            prior = scenario["initial"]
            for step in scenario["steps"]:
                state = step["state"]
                with self.subTest(scenario=scenario["id"], step=step["id"]):
                    self.assertTrue(self.validators["state"].is_valid(state), "actual state schema")
                    self.assertEqual(oracle.state_relation_issues(state), [], "actual source/receipt relations")
                    self.assertEqual(oracle.immutable_transition_issues(prior, state), [], "actual immutable transition")
                    for view in step.get("views", []):
                        self.assertTrue(self.validators["view"].is_valid(view), "actual player view schema")
                        self.assertEqual(oracle.projection_relation_issues(view, state, view["seat_id"]), [], "actual player allowlist")
                    events = step["events"]
                    if events:
                        first = events[0]["id"]
                        binding = state["execution_bindings"][first]
                        self.assertIsNone(events[0]["payload"]["execution_start_event_id"])
                        if step["callback"] == "command":
                            raw = oracle.canonical_payload_json(step["input"]["payload"])
                            self.assertEqual(binding["payload_json"], raw)
                            self.assertEqual(binding["payload_sha256"], digest(raw.encode()))
                            self.assertEqual(binding["correlation_id"], step["input"]["correlation_id"])
                            self.assertEqual(binding["opening_seat_id"], step["input"]["seat_id"])
                        for e in events[1:]: self.assertEqual(e["payload"]["execution_start_event_id"], first)
                        for event in events:
                            self.assertTrue(self.validators["event"].is_valid(event["payload"]))
                            self.assertEqual(state["events"][event["id"]]["execution_start_event_id"], first)
                    self.assertTrue(step["read_only_unchanged"])
                    self.assertEqual(step["patch_count"], int(bool(events)))
                    self.assertTrue(step["root_update"])
                    if step["callback"] == "command":
                        self.assertTrue(step["native_validate_phase"])
                        self.assertTrue(step["native_execute_phase"])
                prior = state

    def test_native_replay_entitlements_restore_and_pause(self):
        r = self.report
        self.assertTrue(r["replay"]["replayed"])
        self.assertTrue(r["replay"]["identical"])
        self.assertEqual(r["replay"]["after_lua_delta"], 0)
        self.assertEqual(r["replay"]["commit_delta"], 0)
        self.assertTrue(r["repeated_settlement"]["same_receipt"])
        self.assertTrue(r["repeated_settlement"]["state_unchanged"])
        self.assertTrue(all(r["checkpoint"].values()))
        s = r["main"]["final"]
        self.assertEqual(s["component_status"], "PAUSED")
        self.assertFalse(s["opening_episode_closed"])
        self.assertFalse(s["campaign_terminal"])
        self.assertFalse(s["service_terminated"])
        self.assertEqual(r["room_end_bridge"], "NOT_RUN")
        self.assertTrue(r["fulfillment_bit_not_transfer_authority"])

    def test_all_complete_payload_codec_vectors(self):
        actual = self.report["codec_cases"]
        expected = self.fixture["payload_codec_vectors"]
        self.assertEqual([x["id"] for x in actual], [x["id"] for x in expected])
        self.assertEqual(len(actual), 36)
        for row, vector in zip(actual, expected):
            with self.subTest(case=row["id"]):
                encoded = oracle.canonical_payload_json(vector["payload"])
                self.assertEqual(row["result"]["payload_json"], encoded)
                self.assertEqual(row["result"]["payload_sha256"], digest(encoded.encode()))
                self.assertEqual(row["result"]["payload_sha256"], vector["payload_sha256"])

    def test_native_identity_source_and_rollback_rejections(self):
        rows = self.report["rejections"]
        self.assertGreaterEqual(len(rows), 20)
        self.assertTrue(all(x["rejected"] and x["unchanged"] for x in rows))
        faults = self.report["faults"]
        self.assertEqual({x["id"] for x in faults}, {"after-lua", "after-schema", "after-go-validation", "before-commit",
                                                     "callback:host.event.emit", "callback:host.state.put", "commit"})
        self.assertTrue(all(x["rejected"] and x["unchanged"] for x in faults))
        self.assertTrue(self.report["branches"]["refuse"])
        self.assertTrue(self.report["branches"]["withdraw"])
        self.assertTrue(self.report["branches"]["needs_evidence"])

    def test_native_unchanged_budgets_and_structural_opening_seats(self):
        self.assertEqual([x["id"] for x in self.report["budgets"]], ["ORDINARY", "MAX_NUL", "MAX_EMOJI", "MAX_ESCAPING"])
        self.assertTrue(all(x["writes"] == 4 and x["passed"] for x in self.report["budgets"]))
        self.assertEqual(self.report["opening_seat_counts"], [2, 3, 4, 5, 6])
        self.assertEqual(self.report["scope"], "FINITE_C01_TASK_PREFIX_NATIVE_ONLY")
        self.assertEqual(self.report["skipped_native_scenarios"], 0)

    def test_strict_entry_requires_explicit_native_source(self):
        with mock.patch.dict(os.environ, {"RR_NATIVE_RUNTIME_REQUIRED": "1"}):
            os.environ.pop("RR_LUA_HOST_REPOSITORY", None)
            with self.assertRaisesRegex(RuntimeError, "requires RR_LUA_HOST_REPOSITORY"):
                run_native()


GO_HARNESS = r'''
package install

import (
    "context"
    "encoding/json"
    "errors"
    "fmt"
    "os"
    "path/filepath"
    "reflect"
    "strconv"
    "strings"
    "sync"
    "testing"

    host "github.com/zyc14588/TRPG_PLATFORM/internal/hostapi"
    rrfixture "github.com/zyc14588/TRPG_PLATFORM/internal/hostapi/hostapitest"
    "github.com/zyc14588/TRPG_PLATFORM/internal/luaruntime/checkpoint"
    "github.com/zyc14588/TRPG_PLATFORM/internal/luaruntime/profile"
    "github.com/zyc14588/TRPG_PLATFORM/internal/luaruntime/vm"
    "github.com/zyc14588/TRPG_PLATFORM/internal/package/archive"
    "github.com/zyc14588/TRPG_PLATFORM/internal/package/capability"
    "github.com/zyc14588/TRPG_PLATFORM/internal/package/dependency"
    "github.com/zyc14588/TRPG_PLATFORM/internal/package/extension"
    "github.com/zyc14588/TRPG_PLATFORM/internal/package/manifest"
    data "github.com/zyc14588/TRPG_PLATFORM/internal/storage/package"
)

const rrA="opening-seat-A"
const rrB="opening-seat-B"
const rrTask="TASK.TEST.CLOCK_OBSERVATION.V1"
const rrText="显示牌变动后回到同一分钟。"

func rrCopy[T any](v T) T { b,_:=json.Marshal(v);var out T;_ = json.Unmarshal(b,&out);return out }
func rrValue(v any) checkpoint.Value {
    switch x:=v.(type) {
    case nil:return checkpoint.Value{Kind:"nil"}
    case bool:return checkpoint.Bool(x)
    case string:return checkpoint.Text(x)
    case float64:return checkpoint.Int(int64(x))
    case json.Number:
        n,e:=strconv.ParseInt(string(x),10,64);if e==nil {return checkpoint.Int(n)}
        f,e:=strconv.ParseFloat(string(x),64);if e!=nil {panic("invalid number test input")}
        return checkpoint.Value{Kind:"float",Number:strconv.FormatFloat(f,'g',-1,64)}
    case []any:a:=[]checkpoint.Value{};for _,v:=range x {a=append(a,rrValue(v))};return checkpoint.Array(a...)
    case map[string]any:m:=map[string]checkpoint.Value{};for k,v:=range x {m[k]=rrValue(v)};return checkpoint.Object(m)
    }
    panic("unsupported native test value")
}
func rrNative(v checkpoint.Value) any {
    switch v.Kind {
    case "nil":return nil
    case "boolean":return v.Boolean
    case "string":return v.String
    case "integer","float":return json.Number(v.Number)
    case "array":a:=[]any{};for _,x:=range v.Array {a=append(a,rrNative(x))};return a
    case "table":m:=map[string]any{};for k,x:=range v.Table {m[k]=rrNative(x)};return m
    }
    panic("invalid observed value")
}
func rrGet(v checkpoint.Value, path ...string) checkpoint.Value {for _,k:=range path {v=v.Table[k]};return v}
func rrMap(v checkpoint.Value) map[string]any {return rrNative(v).(map[string]any)}
func rrRead(t *testing.T,p string) []byte {t.Helper();b,e:=os.ReadFile(p);if e!=nil {t.Fatal("read native input",e)};return b}
func rrJSON(t *testing.T,p string) any {t.Helper();var v any;d:=json.NewDecoder(strings.NewReader(string(rrRead(t,p))));d.UseNumber();if e:=d.Decode(&v);e!=nil {t.Fatal("parse native input",e)};return v}

type rrRepository struct {
    mu sync.Mutex
    snapshot data.Snapshot
    receipts map[string]data.Receipt
    commits []data.Commit
    rollbackCount int
    fault string
    actor,character string
}
type rrTransaction struct {repo *rrRepository;header data.Header;snapshot data.Snapshot;closed bool}
func (r *rrRepository) Begin(ctx context.Context,h data.Header)(data.Transaction,error) {
    r.mu.Lock()
    if h.Binding!=r.snapshot.Binding {r.mu.Unlock();return nil,data.ErrDenied}
    // This synthetic trusted repository binds native principal metadata to the
    // declared slot/character. Real room authorization remains a later probe.
    if r.actor!="" {
        binding:=rrGet(r.snapshot.State,"ledger","opening_seats",r.actor)
        if binding.Kind!="table" || binding.Table["controller_principal"].String!=h.Principal || binding.Table["authorized_character_id"].String!=r.character {
            r.mu.Unlock();return nil,data.ErrDenied
        }
    }
    s:=rrCopy(r.snapshot)
    if saved,ok:=r.receipts[h.CommandID];ok {
        if saved.Header!=h {r.mu.Unlock();return nil,data.ErrConflict};s.Existing=&saved
    } else if s.Version!=h.ExpectedVersion {r.mu.Unlock();return nil,data.ErrConflict}
    return &rrTransaction{repo:r,header:h,snapshot:s},nil
}
func (x *rrTransaction) Snapshot()data.Snapshot{return rrCopy(x.snapshot)}
func (x *rrTransaction) Rollback()error {if !x.closed {x.closed=true;x.repo.rollbackCount++;x.repo.mu.Unlock()};return nil}
func (x *rrTransaction) Commit(ctx context.Context,c data.Commit)(data.Receipt,error) {
    if ctx.Err()!=nil {return data.Receipt{},ctx.Err()};if x.repo.fault=="commit" {return data.Receipt{},errors.New("injected transaction commit failure")}
    r:=data.Receipt{Header:c.Header,Version:c.Header.ExpectedVersion+1,Result:c.Result,Inputs:c.Inputs,Events:c.Events}
    x.repo.snapshot.Version=r.Version;x.repo.snapshot.State=rrCopy(c.State)
    x.repo.commits=append(x.repo.commits,rrCopy(c));x.repo.receipts[c.Header.CommandID]=rrCopy(r)
    x.Rollback();return rrCopy(r),nil
}
type rrEnvironment struct {
    t *testing.T; runner string;pkg *archive.Package;contract HostContract
    serial int;callbacks map[string]bool;report map[string]any
}
type rrSession struct {env *rrEnvironment;session *vm.Session;repo *rrRepository;service *host.Service;options host.Options;commands int;afterLua int;fault string}
func (e *rrEnvironment) new(seed checkpoint.Value)*rrSession {
    e.t.Helper();e.serial++
    policy,err:=capability.NewTrustPolicy(map[capability.TrustLevel][]string{capability.TrustOfficial:{"host.state","host.event"},capability.TrustSigned:{"host.state","host.event"},capability.TrustPrivateUnverified:{"host.state","host.event"},capability.TrustDevelopment:{"host.state","host.event"}})
    if err!=nil {e.t.Fatal("native trust policy",err)}
    grants,err:=capability.NewGrantSet([]string{"host.state","host.event"});if err!=nil {e.t.Fatal("native grants",err)}
    d,_:=e.pkg.Manifest();id:=string(d.Package.PackageID)
    s,err:=vm.New(context.Background(),vm.Options{SessionID:fmt.Sprintf("task-prefix-%d",e.serial),Runner:e.runner,Package:e.pkg,State:vm.State{Version:1,Value:seed},Limits:profile.DefaultLimits(),Audit:func(profile.Audit)error{return nil},Host:&vm.HostOptions{Trust:map[string]capability.TrustLevel{id:capability.TrustPrivateUnverified},Policy:policy,Execution:grants}})
    if err!=nil {e.t.Fatal("actual game entrypoint load",profile.Code(err))}
    e.t.Cleanup(func(){_ = s.Destroy()})
    r:=&rrRepository{receipts:map[string]data.Receipt{}}
    o,err:=e.contract.bind(s,map[string]*archive.Package{id:e.pkg},r,"task-prefix-workspace")
    if err!=nil {e.t.Fatal("native schema bind",profile.Code(err))}
    r.snapshot=data.Snapshot{Binding:o.Binding,Version:1,State:rrCopy(seed),SchemaHash:o.StateSchema.Digest()}
    x:=&rrSession{env:e,session:s,repo:r,options:o}
    o.Fault=func(ctx context.Context,point string)error {if point=="after-lua" {x.afterLua++};if point==x.fault {return errors.New("injected native stage failure")};return nil}
    x.options=o;x.service,err=host.New(o);if err!=nil {e.t.Fatal("native Host constructor",profile.Code(err))}
    return x
}
func (x *rrSession) command(callback,seat string,input checkpoint.Value)host.Command {
    x.commands++
    principal:="trusted-lifecycle"
    if seat!="" {principal=rrGet(x.repo.snapshot.State,"ledger","opening_seats",seat,"controller_principal").String}
    if principal=="" {principal="missing-trusted-seat"}
    return host.Command{Callback:callback,ID:fmt.Sprintf("native-command-%04d",x.commands),Principal:principal,ExpectedVersion:x.repo.snapshot.Version,Input:input,Random:[]int64{}}
}
func (x *rrSession) execute(c host.Command)(data.Receipt,error) {
    seat:=c.Input.Table["seat_id"].String
    x.repo.actor=seat;x.repo.character=rrGet(x.repo.snapshot.State,"ledger","opening_seats",seat,"authorized_character_id").String
    return x.service.Execute(context.Background(),x.session.Token(),c)
}
func (x *rrSession) read(callback,seat string,input checkpoint.Value)(data.Receipt,error) {
    c:=x.command(callback,seat,input)
    x.repo.actor=seat;x.repo.character=rrGet(x.repo.snapshot.State,"ledger","opening_seats",seat,"authorized_character_id").String
    return x.service.Read(context.Background(),x.session.Token(),c)
}
func (x *rrSession) mustRead(callback,seat string,input checkpoint.Value)checkpoint.Value {
    x.env.t.Helper();before:=rrCopy(x.repo.snapshot);commits:=len(x.repo.commits)
    r,err:=x.read(callback,seat,input);if err!=nil {x.env.t.Fatal("native read "+callback,profile.Code(err))}
    if !reflect.DeepEqual(before,x.repo.snapshot)||commits!=len(x.repo.commits) {x.env.t.Fatal("native read mutated authority")}
    x.env.callbacks[callback]=true;return r.Result
}
func (x *rrSession) apply(seat string,p map[string]any,correlation string)map[string]any {
    input:=rrValue(map[string]any{"type":"task-prefix","seat_id":seat,"correlation_id":correlation,"payload":p})
    return x.applyNative(x.command("command",seat,input))
}
func (x *rrSession) applyNative(c host.Command)map[string]any {
    x.env.t.Helper();before:=rrCopy(x.repo.snapshot)
    x.env.report["progress"]=map[string]any{"scenario":x.env.serial,"command":x.commands,"action":c.Input.Table["payload"].Table["action"].String}
    r,err:=x.execute(c);if err!=nil {x.env.t.Fatal("native callback "+c.Callback,"scenario",x.env.serial,"command",x.commands,"action",c.Input.Table["payload"].Table["action"].String,profile.Code(err))}
    x.env.callbacks[c.Callback]=true
    if c.Callback=="command" {x.env.callbacks["validate_command"]=true;x.env.callbacks["execute_command"]=true}
    events:=[]any{};for _,event:=range r.Events {events=append(events,map[string]any{"id":event.ID,"type":event.Type,"payload":rrNative(event.Payload)})}
    commit:=x.repo.commits[len(x.repo.commits)-1]
    rootUpdate:=true;for _,patch:=range commit.Patches {if len(patch.Path)!=0 {rootUpdate=false}}
    validatePhase,executePhase:=false,false
    for _,audit:=range commit.Audit {if audit.Phase=="validate" {validatePhase=true};if audit.Phase=="execute" {executePhase=true}}
    views:=[]any{}
    for _,seat:=range []string{rrA,rrB} {
        if rrGet(x.repo.snapshot.State,"ledger","seats",seat).Kind=="table" {
            views=append(views,rrNative(x.mustRead("project_view",seat,rrValue(map[string]any{"seat_id":seat}))))
        }
    }
    if reflect.DeepEqual(before.State,x.repo.snapshot.State)&&len(r.Events)>0 {x.env.t.Fatal("emission absent from authoritative State")}
    return map[string]any{"id":c.ID,"callback":c.Callback,"input":rrNative(c.Input),"result":rrNative(r.Result),"events":events,"state":rrNative(x.repo.snapshot.State),"views":views,"patch_count":len(commit.Patches),"root_update":rootUpdate,"read_only_unchanged":true,"native_validate_phase":validatePhase,"native_execute_phase":executePhase}
}
func rrPayload(action string)map[string]any {
    if action=="WATCH" {return map[string]any{"action":action,"target":"target.departure_board"}}
    return map[string]any{"action":action,"task_id":rrTask}
}
func rrScenario(x *rrSession,id string)map[string]any {return map[string]any{"id":id,"initial":rrNative(x.repo.snapshot.State),"steps":[]any{}}}
func rrAdd(s map[string]any,step map[string]any){s["steps"]=append(s["steps"].([]any),step)}
func rrObservation(x *rrSession,seat string)string{return rrGet(x.repo.snapshot.State,"ledger","seats",seat,"own_inspection_event_id").String}
func rrPaper(x *rrSession,seat string)string {
    rid:=rrGet(x.repo.snapshot.State,"ledger","seats",seat,"settlement_receipt_id").String
    return rrGet(x.repo.snapshot.State,"ledger","receipts",rid,"paper_id").String
}
func rrSubmission(x *rrSession,seat string)map[string]any{return map[string]any{"action":"SUBMIT_OBSERVATION","task_id":rrTask,"observation_event_id":rrObservation(x,seat),"recipient":"npc.lin-que","description":rrText}}
func rrSettled(e *rrEnvironment,seed checkpoint.Value)(*rrSession,map[string]any) {
    x:=e.new(seed);s:=rrScenario(x,"naturally-settled-two-seat")
    for _,item:=range []struct{seat,action string}{{rrA,"PUBLISH_TASK"},{rrA,"ACCEPT_TASK"},{rrB,"ACCEPT_TASK"},{rrA,"WATCH"},{rrB,"WATCH"}} {rrAdd(s,x.apply(item.seat,rrPayload(item.action),"settled-"+item.action+item.seat))}
    for _,seat:=range []string{rrA,rrB} {
        rrAdd(s,x.apply(seat,rrSubmission(x,seat),"settled-report"+seat))
        rrAdd(s,x.apply(seat,rrPayload("ADJUDICATE_TASK"),"settled-adjudicate"+seat))
        rrAdd(s,x.apply(seat,rrPayload("SETTLE_TASK"),"settled-transfer"+seat))
    }
    return x,s
}
func rrReject(x *rrSession,id string,c host.Command)map[string]any {
    before:=rrCopy(x.repo.snapshot);commits:=len(x.repo.commits);receipts:=len(x.repo.receipts)
    _,err:=x.execute(c)
    return map[string]any{"id":id,"rejected":err!=nil,"unchanged":reflect.DeepEqual(before,x.repo.snapshot)&&commits==len(x.repo.commits)&&receipts==len(x.repo.receipts),"error_code":profile.Code(err)}
}

func TestNativeTaskPrefixContent(t *testing.T) {
    spec:=rrJSON(t,os.Getenv("RR_GAME_SPEC")).(map[string]any);root:=spec["root"].(string)
    report:=map[string]any{"complete":false,"scope":"FINITE_C01_TASK_PREFIX_NATIVE_ONLY","room_end_bridge":"NOT_RUN","skipped_native_scenarios":0,"native_limits":profile.DefaultLimits(),"native_budget":host.DefaultBudget()}
    defer func(){b,err:=json.Marshal(report);if err!=nil {t.Error("native report encode",err);return};if err=os.WriteFile(os.Getenv("RR_GAME_REPORT"),b,0664);err!=nil {t.Error("native report save",err)}}()
    module,err:=filepath.Abs("../../..");if err!=nil {t.Fatal(err)}
    runner,err:=rrfixture.BuildRunner(module,t.TempDir());if err!=nil {t.Fatal("native runner build",err)}
    report["runner_hash"]=checkpoint.Hash(rrRead(t,runner))
    manifestBytes:=rrRead(t,filepath.Join(root,"manifest.yaml"));document,err:=manifest.Parse(manifestBytes);if err!=nil {t.Fatal("native manifest parse",err)}
    packageID:=string(document.Package.PackageID)
    locked,err:=dependency.NewLockedPackage(packageID,"0.1.0","sha256:"+strings.Repeat("0",64),nil,nil);if err!=nil {t.Fatal(err)}
    lock,err:=dependency.BuildExactLock(packageID,[]dependency.LockedPackage{locked});if err!=nil {t.Fatal(err)}
    files:=map[string][]byte{archive.ManifestPath:manifestBytes}
    for _,name:=range []string{"lua/main.lua","lua/task_prefix.lua","schemas/state.schema.json","schemas/result.schema.json","schemas/event.schema.json","schemas/view.schema.json","schemas/command.schema.json"} {files[name]=rrRead(t,filepath.Join(root,name))}
    pkg,err:=archive.FromFiles(files,lock,extension.DefaultSupport);if err!=nil {t.Fatal("actual game archive",err)}
    report["archive_hash"]=string(pkg.ContentHash())
    contractJSON:=rrJSON(t,filepath.Join(root,"contract.json")).(map[string]any)
    callbacksJSON:=rrJSON(t,filepath.Join(root,"fixtures/native-callback-cases.json")).(map[string]any)
    callbackSeeds:=map[string]checkpoint.Value{}
    for _,row:=range callbacksJSON["cases"].([]any) {item:=row.(map[string]any)["host_case"].(map[string]any);callbackSeeds[item["Callback"].(string)]=rrValue(item["Expected"])}
    seed:=rrValue(rrJSON(t,filepath.Join(root,"fixtures/initial-state.json")))
    index:=contractJSON["host_contract_index"].(map[string]any)
    reference:=func(raw any,value checkpoint.Value)SchemaReference {r:=raw.(map[string]any);return SchemaReference{PackageID:r["package_id"].(string),Path:r["path"].(string),Digest:"sha256:"+r["sha256"].(string),Seed:value}}
    contract:=HostContract{State:reference(index["State"],seed),Result:reference(index["Result"],callbackSeeds["command"]),Results:map[string]SchemaReference{},Events:map[string]SchemaReference{},Budget:host.DefaultBudget()}
    for name,raw:=range index["Results"].(map[string]any) {contract.Results[name]=reference(raw,callbackSeeds[name])}
    sourceFixture:=rrJSON(t,filepath.Join(root,"fixtures/task-prefix-cases.json")).(map[string]any)
    for name,raw:=range index["Events"].(map[string]any) {contract.Events[name]=reference(raw,rrValue(sourceFixture["emitted_events"].([]any)[3]))}
    if err=contract.validate();err!=nil {t.Fatal("native HostContract admission",err)}
    e:=&rrEnvironment{t:t,runner:runner,pkg:pkg,contract:contract,callbacks:map[string]bool{},report:report}
    x:=e.new(seed);main:=rrScenario(x,"actual-two-seat-flow")
    for _,name:=range []string{"on_session_create","on_session_start"} {
        c:=x.command(name,"",checkpoint.Object(map[string]checkpoint.Value{}));_,err=x.execute(c);if err!=nil {t.Fatal("native lifecycle",profile.Code(err))};e.callbacks[name]=true
    }
    corr:=0
    apply:=func(seat string,p map[string]any)map[string]any {corr++;step:=x.apply(seat,p,fmt.Sprintf("fixture-correlation-%02d",corr));rrAdd(main,step);return step}
    apply(rrA,rrPayload("PUBLISH_TASK"));apply(rrA,rrPayload("ACCEPT_TASK"));apply(rrB,rrPayload("ACCEPT_TASK"));apply(rrA,rrPayload("WATCH"));apply(rrB,rrPayload("WATCH"))
    apply(rrA,rrSubmission(x,rrA));apply(rrA,rrPayload("ADJUDICATE_TASK"));settlement:=apply(rrA,rrPayload("SETTLE_TASK"))
    original:=x.repo.commits[len(x.repo.commits)-1]
    replayCommand:=host.Command{Callback:original.Inputs.Callback,ID:original.Header.CommandID,Principal:original.Header.Principal,ExpectedVersion:original.Header.ExpectedVersion,Input:original.Inputs.Command,Time:original.Inputs.Time,Random:original.Inputs.Random,Envelope:original.Inputs.Envelope}
    afterLua,commits:=x.afterLua,len(x.repo.commits);saved:=rrCopy(x.repo.receipts[replayCommand.ID]);replay,err:=x.execute(replayCommand);if err!=nil {t.Fatal("same-command replay",profile.Code(err))}
    replayCopy:=rrCopy(replay);savedCopy:=rrCopy(saved)
    report["replay"]=map[string]any{"replayed":replay.Replayed,"identical":reflect.DeepEqual(replayCopy,savedCopy),"after_lua_delta":x.afterLua-afterLua,"commit_delta":len(x.repo.commits)-commits}
    repeatBefore:=rrCopy(x.repo.snapshot.State);repeat:=x.apply(rrA,rrPayload("SETTLE_TASK"),"different-native-command-correlation")
    report["repeated_settlement"]=map[string]any{"same_receipt":reflect.DeepEqual(repeat["result"].(map[string]any)["settlement_receipt"],settlement["result"].(map[string]any)["settlement_receipt"]),"state_unchanged":reflect.DeepEqual(repeatBefore,x.repo.snapshot.State)}
    apply(rrA,map[string]any{"action":"WRITE_OWN_PAPER","paper_id":rrPaper(x,rrA),"source_event_id":rrObservation(x,rrA),"text":rrText})
    apply(rrA,map[string]any{"action":"SHARE_SOURCE","source_event_id":rrObservation(x,rrA),"recipient_seat_ids":[]any{rrB},"record_kind":"RAW_OBSERVATION","text":rrText})
    apply(rrB,rrSubmission(x,rrB));apply(rrB,rrPayload("ADJUDICATE_TASK"));apply(rrB,rrPayload("SETTLE_TASK"))
    rrAdd(main,x.applyNative(x.command("on_session_end","",checkpoint.Object(map[string]checkpoint.Value{}))))
    main["final"]=rrNative(x.repo.snapshot.State);allEvents:=[]any{};for _,commit:=range x.repo.commits {for _,event:=range commit.Events {allEvents=append(allEvents,map[string]any{"id":event.ID,"payload":rrNative(event.Payload)})}};main["events"]=allEvents;report["main"]=main
    x.mustRead("list_legal_actions",rrA,rrValue(map[string]any{"seat_id":rrA}))
    full:=x.mustRead("create_checkpoint","",checkpoint.Object(map[string]checkpoint.Value{}))
    captured,err:=x.session.CaptureHost(context.Background(),x.session.Token(),x.session.SessionID(),func(ctx context.Context,call profile.HostCall)(checkpoint.Value,error){
        if call.Capability!="host.state"||call.Operation!="get"||len(call.Arguments)!=1 {return checkpoint.Value{},errors.New("capture read capability")}
        v:=rrCopy(x.repo.snapshot.State);for _,k:=range call.Arguments[0].Array {v=v.Table[k.String]};return v,nil
    });if err!=nil {t.Fatal("CaptureHost nil-argument checkpoint",profile.Code(err))}
    encoded,err:=checkpoint.Encode(captured);if err!=nil {t.Fatal("checkpoint encode",err)};decoded,err:=checkpoint.Decode(encoded,captured.Binding);if err!=nil {t.Fatal("checkpoint decode",err)}
    authoritative:=rrCopy(x.repo.snapshot)
    if err=x.session.Reconstruct(context.Background(),vm.State{Version:authoritative.Version,Value:authoritative.State},&decoded);err!=nil {t.Fatal("native checkpoint reconstruct",profile.Code(err))}
    restored:=x.mustRead("restore_checkpoint","",decoded.State)
    resumed:=x.mustRead("on_session_restore","",authoritative.State)
    x.mustRead("on_safe_migration_boundary","",checkpoint.Object(map[string]checkpoint.Value{}));x.mustRead("cleanup","",checkpoint.Object(map[string]checkpoint.Value{}))
    _,err=x.execute(x.command("resume_continuation","",checkpoint.Object(map[string]checkpoint.Value{})));if err!=nil {t.Fatal("native unsupported continuation",profile.Code(err))};e.callbacks["resume_continuation"]=true
    report["checkpoint"]=map[string]any{"read_full":reflect.DeepEqual(full,authoritative.State),"capture_nil_full":reflect.DeepEqual(captured.State,authoritative.State),"encode_decode":reflect.DeepEqual(decoded,captured),"reconstruct_preserved":reflect.DeepEqual(authoritative.State,x.repo.snapshot.State),"restore_value_shape":restored.Table["status"].String=="RESTORED","restore_state_shape":resumed.Table["status"].String=="RESTORED"}
    fresh:=e.new(seed);callbackResults:=[]any{}
    for _,raw:=range callbacksJSON["cases"].([]any) {
        item:=raw.(map[string]any)["host_case"].(map[string]any);name:=item["Callback"].(string)
        if name=="command" {continue}
        input:=rrValue(item["Input"]);var actual checkpoint.Value
        if name=="on_session_create"||name=="on_session_start"||name=="on_session_end"||name=="resume_continuation" {
            c:=fresh.command(name,"",input);r,err:=fresh.execute(c);if err!=nil {t.Fatal("exact native callback",name,profile.Code(err))};e.callbacks[name]=true;actual=r.Result
        } else {seat:=input.Table["seat_id"].String;actual=fresh.mustRead(name,seat,input)}
        callbackResults=append(callbackResults,map[string]any{"callback":name,"exact_expected_result":reflect.DeepEqual(rrNative(actual),rrNative(rrValue(item["Expected"]))),"input":rrNative(input),"result":rrNative(actual)})
    };report["callback_results"]=callbackResults
    scenarios:=[]any{main}
    // A complete real flow supplies all subsequent seeded branch/fault tests.
    settled,settledScenario:=rrSettled(e,seed);scenarios=append(scenarios,settledScenario)
    base:=rrCopy(settled.repo.snapshot.State)
    budgets:=[]any{}
    for _,raw:=range spec["budget_cases"].([]any) {
        item:=raw.(map[string]any);b:=e.new(base);scenario:=rrScenario(b,"writes-"+item["id"].(string))
        for i,value:=range item["texts"].([]any) {seat:=rrA;if i%2==1 {seat=rrB};rrAdd(scenario,b.apply(seat,map[string]any{"action":"WRITE_OWN_PAPER","paper_id":rrPaper(b,seat),"source_event_id":rrObservation(b,seat),"text":value},fmt.Sprintf("write-%d",i)))}
        scenarios=append(scenarios,scenario);budgets=append(budgets,map[string]any{"id":item["id"],"writes":4,"passed":true})
    }
    report["budgets"]=budgets
    for _,order:=range [][]any{{rrA,rrB},{rrB,rrA}} {
        share:=e.new(base);scenario:=rrScenario(share,"ordered-share")
        rrAdd(scenario,share.apply(rrA,map[string]any{"action":"SHARE_SOURCE","source_event_id":rrObservation(share,rrA),"recipient_seat_ids":order,"record_kind":"RAW_OBSERVATION","text":rrText},"ordered-share"));scenarios=append(scenarios,scenario)
    }
    written:=e.new(base);writtenScenario:=rrScenario(written,"owned-paper-text-share")
    rrAdd(writtenScenario,written.apply(rrA,map[string]any{"action":"WRITE_OWN_PAPER","paper_id":rrPaper(written,rrA),"source_event_id":rrObservation(written,rrA),"text":"exact owned paper text"},"own-paper-write"))
    writeID:=rrGet(written.repo.snapshot.State,"ledger","papers",rrPaper(written,rrA),"write_event_id").String
    rrAdd(writtenScenario,written.apply(rrA,map[string]any{"action":"SHARE_SOURCE","source_event_id":writeID,"recipient_seat_ids":[]any{rrB,rrA},"record_kind":"PAPER_TEXT","text":"exact owned paper text"},"own-paper-share"));scenarios=append(scenarios,writtenScenario)
    // Trusted private-note seed, projected through the actual callback.
    notes:=rrCopy(base)
    for _,seat:=range []string{rrA,rrB} {row:=notes.Table["ledger"].Table["seats"].Table[seat];row.Table["private_notes"]=rrValue([]any{map[string]any{"note_id":"private-note-"+seat,"author_seat_id":seat,"source_event_ids":map[string]any{rrGet(notes,"ledger","seats",seat,"own_inspection_event_id").String:true},"kind":"PLAYER_CLAIM","text":"private note for "+seat}})}
    private:=e.new(notes);scenario:=rrScenario(private,"trusted-private-notes")
    rrAdd(scenario,private.apply(rrA,map[string]any{"action":"SHARE_SOURCE","source_event_id":rrObservation(private,rrA),"recipient_seat_ids":[]any{rrB},"record_kind":"PLAYER_CLAIM","text":"explicitly delivered claim"},"voluntary-claim"));scenarios=append(scenarios,scenario)
    report["scenarios"]=scenarios
    branches:=map[string]any{}
    for _,pair:=range []struct{action,key,expected string}{{"REFUSE_TASK","refuse","DECLINED"},{"WITHDRAW_TASK","withdraw","WITHDRAWN"},{"ADJUDICATE_TASK","needs_evidence","NEEDS_EVIDENCE"}} {
        b:=e.new(seed);b.apply(rrA,rrPayload("PUBLISH_TASK"),"branch-publish");b.apply(rrA,rrPayload("ACCEPT_TASK"),"branch-accept");step:=b.apply(rrA,rrPayload(pair.action),"branch-action")
        if pair.key=="needs_evidence" {branches[pair.key]=step["result"].(map[string]any)["status"]==pair.expected} else {branches[pair.key]=rrGet(b.repo.snapshot.State,"ledger","seats",rrA,"participation").String==pair.expected}
    };report["branches"]=branches
    // The GM fulfillment bit is explicitly absent from the transfer decision.
    adjudicated:=rrCopy(settled.repo.commits[6].State)
    adjudicated.Table["ledger"].Table["seats"].Table[rrA].Table["actual_fulfillment_internal"]=checkpoint.Bool(false)
    bit:=e.new(adjudicated);bitStep:=bit.apply(rrA,rrPayload("SETTLE_TASK"),"gm-bit-does-not-authorize")
    report["fulfillment_bit_not_transfer_authority"]=bitStep["result"].(map[string]any)["status"]=="SETTLED"
    rejections:=[]any{}
    invalids:=[]struct{id,seat string;p map[string]any}{
        {"client-seat-authority",rrA,map[string]any{"action":"WATCH","target":"target.departure_board","seat_id":rrB}},
        {"client-event-authority",rrA,map[string]any{"action":"WATCH","target":"target.departure_board","event_id":"evt-ffffffffffffffffffffffffffffffff"}},
        {"wrong-task-instance",rrA,map[string]any{"action":"SETTLE_TASK","task_id":"new-task-instance"}},
        {"forged-event",rrA,map[string]any{"action":"SUBMIT_OBSERVATION","task_id":rrTask,"observation_event_id":"evt-ffffffffffffffffffffffffffffffff","recipient":"npc.lin-que","description":rrText}},
        {"foreign-personal-source",rrA,map[string]any{"action":"SUBMIT_OBSERVATION","task_id":rrTask,"observation_event_id":rrObservation(settled,rrB),"recipient":"npc.lin-que","description":rrText}},
        {"foreign-paper",rrB,map[string]any{"action":"WRITE_OWN_PAPER","paper_id":rrPaper(settled,rrA),"source_event_id":rrObservation(settled,rrA),"text":rrText}},
        {"unseen-source",rrA,map[string]any{"action":"SHARE_SOURCE","source_event_id":rrObservation(settled,rrB),"recipient_seat_ids":[]any{rrB},"record_kind":"RAW_OBSERVATION","text":rrText}},
        {"invented-raw-text",rrA,map[string]any{"action":"SHARE_SOURCE","source_event_id":rrObservation(settled,rrA),"recipient_seat_ids":[]any{rrB},"record_kind":"RAW_OBSERVATION","text":"invented"}},
        {"unknown-recipient",rrA,map[string]any{"action":"SHARE_SOURCE","source_event_id":rrObservation(settled,rrA),"recipient_seat_ids":[]any{"foreign-seat"},"record_kind":"RAW_OBSERVATION","text":rrText}},
        {"duplicate-recipient",rrA,map[string]any{"action":"SHARE_SOURCE","source_event_id":rrObservation(settled,rrA),"recipient_seat_ids":[]any{rrB,rrB},"record_kind":"RAW_OBSERVATION","text":rrText}},
        {"tick-boundary",rrA,rrPayload("WATCH")},
    }
    for _,action:=range []string{"PROBE_DISPLAY","SOCIAL_INFLUENCE","FULL_LISTEN","MOVE","TRY_EXIT"} {invalids=append(invalids,struct{id,seat string;p map[string]any}{"unsupported-"+action,rrA,map[string]any{"action":action}})}
    for _,item:=range invalids {b:=e.new(base);input:=rrValue(map[string]any{"type":"task-prefix","seat_id":item.seat,"correlation_id":"invalid-command","payload":item.p});rejections=append(rejections,rrReject(b,item.id,b.command("command",item.seat,input)))}
    for _,field:=range []string{"seat_id","correlation_id","type","payload"} {b:=e.new(seed);input:=rrValue(map[string]any{"type":"task-prefix","seat_id":rrA,"correlation_id":"missing-field","payload":rrPayload("WATCH")});delete(input.Table,field);rejections=append(rejections,rrReject(b,"missing-"+field,b.command("command",rrA,input)))}
    for _,change:=range []string{"foreign-run-receipt","foreign-loop-receipt","missing-seed-seat","paused","inaccessible","unadjudicated","foreign-holder","forged-receipt-source","orphan-receipt","bad-source-binding","foreign-private-note"} {
        initial:=rrCopy(base)
        if change=="missing-seed-seat" {delete(initial.Table["ledger"].Table["opening_seats"].Table,rrA)}
        if change=="paused" {initial.Table["component_status"]=checkpoint.Text("PAUSED")}
        if change=="inaccessible"||change=="unadjudicated" {initial=rrCopy(settled.repo.commits[6].State)}
        if change=="inaccessible" {initial.Table["ledger"].Table["seats"].Table[rrA].Table["access_status"]=checkpoint.Text("UNAVAILABLE_ISSUER")}
        if change=="unadjudicated" {initial=rrCopy(settled.repo.commits[5].State)}
        for _,r:=range initial.Table["ledger"].Table["receipts"].Table {
            if change=="foreign-run-receipt" {r.Table["run_id"]=checkpoint.Text("foreign-run")}
            if change=="foreign-loop-receipt" {r.Table["legitimate_loop_id"]=checkpoint.Text("foreign-loop")}
        }
        if change=="foreign-holder" {initial.Table["ledger"].Table["papers"].Table[rrPaper(settled,rrA)].Table["holder_seat_id"]=checkpoint.Text(rrB)}
        if change=="forged-receipt-source" {rid:=rrGet(initial,"ledger","seats",rrA,"settlement_receipt_id").String;initial.Table["ledger"].Table["receipts"].Table[rid].Table["source_event_ids"]=rrValue(map[string]any{"evt-ffffffffffffffffffffffffffffffff":true})}
        if change=="orphan-receipt" {rid:=rrGet(initial,"ledger","seats",rrA,"settlement_receipt_id").String;initial.Table["ledger"].Table["receipts"].Table["orphan-receipt"]=rrCopy(initial.Table["ledger"].Table["receipts"].Table[rid])}
        if change=="bad-source-binding" {watch:=rrGet(initial,"ledger","seats",rrA,"own_inspection_event_id").String;start:=rrGet(initial,"events",watch,"execution_start_event_id").String;initial.Table["execution_bindings"].Table[start].Table["payload_sha256"]=checkpoint.Text("sha256:"+strings.Repeat("0",64))}
        if change=="foreign-private-note" {initial.Table["ledger"].Table["seats"].Table[rrA].Table["private_notes"]=rrValue([]any{map[string]any{"note_id":"foreign-note","author_seat_id":rrB,"source_event_ids":map[string]any{rrObservation(settled,rrB):true},"kind":"PLAYER_CLAIM","text":"hidden other-seat note"}})}
        b:=e.new(initial);input:=rrValue(map[string]any{"type":"task-prefix","seat_id":rrA,"correlation_id":"invalid-seed","payload":rrPayload("SETTLE_TASK")});rejections=append(rejections,rrReject(b,change,b.command("command",rrA,input)))
    }
    for _,kind:=range []string{"controller","character"} {
        b:=e.new(seed);input:=rrValue(map[string]any{"type":"task-prefix","seat_id":rrA,"correlation_id":"identity-negative","payload":rrPayload("WATCH")});c:=b.command("command",rrA,input)
        b.repo.actor=rrA;b.repo.character=rrGet(seed,"ledger","opening_seats",rrA,"authorized_character_id").String
        if kind=="controller" {c.Principal="fixture-principal-B"} else {b.repo.character="fixture-character-B"}
        before:=rrCopy(b.repo.snapshot);_,err=b.service.Execute(context.Background(),b.session.Token(),c)
        rejections=append(rejections,map[string]any{"id":"trusted-"+kind,"rejected":err!=nil,"unchanged":reflect.DeepEqual(before,b.repo.snapshot),"error_code":profile.Code(err)})
    }
    for _,kind:=range []string{"player-view-checkpoint","corrupt-checkpoint-receipt","player-view-session-restore"} {
        b:=e.new(base);input:=rrCopy(base);callback:="restore_checkpoint"
        if kind=="corrupt-checkpoint-receipt" {rid:=rrGet(input,"ledger","seats",rrA,"settlement_receipt_id").String;input.Table["ledger"].Table["receipts"].Table[rid].Table["paper_id"]=checkpoint.Text("forged-paper")
        } else {input=b.mustRead("project_view",rrA,rrValue(map[string]any{"seat_id":rrA}));if kind=="player-view-session-restore" {callback="on_session_restore"}}
        before:=rrCopy(b.repo.snapshot);commits:=len(b.repo.commits);_,err:=b.read(callback,"",input)
        rejections=append(rejections,map[string]any{"id":kind,"rejected":err!=nil,"unchanged":reflect.DeepEqual(before,b.repo.snapshot)&&len(b.repo.commits)==commits,"error_code":profile.Code(err)})
    };report["rejections"]=rejections
    faults:=[]any{}
    for _,point:=range []string{"after-lua","after-schema","after-go-validation","before-commit","callback:host.event.emit","callback:host.state.put","commit"} {
        b:=e.new(seed);b.fault=point;if point=="commit" {b.repo.fault=point}
        input:=rrValue(map[string]any{"type":"task-prefix","seat_id":rrA,"correlation_id":"fault-injection","payload":rrPayload("PUBLISH_TASK")});faults=append(faults,rrReject(b,point,b.command("command",rrA,input)))
    };report["faults"]=faults
    negativeCases:=[]any{}
    for _,raw:=range callbacksJSON["native_hostcase_negatives"].([]any) {
        item:=raw.(map[string]any);c:=HostCase{Callback:item["callback"].(string),Input:checkpoint.Object(map[string]checkpoint.Value{}),Expected:callbackSeeds["command"]}
        if value,ok:=item["time"];ok {n,_:=strconv.ParseInt(string(value.(json.Number)),10,64);c.Time=n}
        negativeCases=append(negativeCases,map[string]any{"id":item["id"],"passed":c.validate()!=nil})
    };report["hostcase_negatives"]=negativeCases
    schemaCases:=[]any{};schemaMap:=map[string]host.Schema{}
    for name,value:=range map[string]checkpoint.Value{"state":seed,"result":callbackSeeds["command"],"view":callbackSeeds["project_view"],"event":rrValue(sourceFixture["emitted_events"].([]any)[3]),"command":rrValue(rrPayload("WATCH"))} {
        path:="schemas/"+name+".schema.json";entry,_:=pkg.Entry(path);schemaMap[name],err=host.BindSchema(pkg,path,checkpoint.Hash(entry.Bytes()),value);if err!=nil {t.Fatal("native schema",name,profile.Code(err))}
    }
    for _,raw:=range spec["schema_cases"].([]any) {item:=raw.(map[string]any);name:=strings.TrimSuffix(strings.TrimPrefix(item["schema"].(string),"schemas/"),".schema.json");err=schemaMap[name].Validate(rrValue(item["value"]));schemaCases=append(schemaCases,map[string]any{"id":item["id"],"passed":(err==nil)==item["valid"].(bool)})};report["schema_cases"]=schemaCases
    codecCases:=[]any{}
    for _,raw:=range spec["codec_cases"].([]any) {
        item:=raw.(map[string]any);engine,err:=profile.New(profile.Config{Limits:profile.DefaultLimits(),Modules:map[string][]byte{"lua/task_prefix.lua":files["lua/task_prefix.lua"]}});if err!=nil {t.Fatal("native codec engine",profile.Code(err))}
        result,err:=engine.Execute(context.Background(),[]byte(item["source"].(string)));engine.Close();if err!=nil||len(result.Values)!=1 {t.Fatal("actual Lua codec",item["id"],profile.Code(err))}
        codecCases=append(codecCases,map[string]any{"id":item["id"],"result":rrNative(result.Values[0]),"entry":"ISOLATED_ACTUAL_IMPLEMENTATION_CODEC_ONLY"})
    };report["codec_cases"]=codecCases
    counts:=[]int{}
    for n:=2;n<=6;n++ {
        extended:=rrCopy(seed)
        for i:=2;i<n;i++ {seat:=fmt.Sprintf("opening-seat-%c",'A'+i);extended.Table["ledger"].Table["opening_seats"].Table[seat]=rrValue(map[string]any{"controller_principal":"trusted-principal-"+seat,"authorized_character_id":"trusted-character-"+seat});extended.Table["ledger"].Table["seats"].Table[seat]=rrCopy(rrGet(seed,"ledger","seats",rrA));extended.Table["ledger"].Table["papers"].Table["paper-"+seat]=rrCopy(rrGet(seed,"ledger","papers","paper-fixture-A"))}
        b:=e.new(extended);c:=b.command("on_session_create","",checkpoint.Object(map[string]checkpoint.Value{}));_,err=b.execute(c);if err!=nil {t.Fatal("trusted structural seat count",n,profile.Code(err))};counts=append(counts,n)
    };report["opening_seat_counts"]=counts
    callbackNames:=[]string{};for name:=range e.callbacks {if name!="command" {callbackNames=append(callbackNames,name)}};report["callbacks"]=callbackNames
    report["complete"]=true
}
'''
