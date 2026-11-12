#!/usr/bin/env python3
"""Static MT8163 Android audio-stack and DSP-driver inventory."""
from __future__ import annotations
import argparse, hashlib, json, re, shutil, subprocess, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

def digest(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def cmd(args):
    try:
        return subprocess.run(args,capture_output=True,text=True,errors="replace",timeout=30).stdout
    except Exception as e:
        return str(e)

def elf(p):
    h=cmd(["readelf","-h",str(p)])
    n=cmd(["readelf","-n",str(p)])
    d=cmd(["readelf","-d",str(p)])
    def field(k):
        m=re.search(r"^\s*"+k+r":\s*(.+)$",h,re.M)
        return m.group(1).strip() if m else None
    m=re.search(r"Build ID:\s*([0-9a-fA-F]+)",n)
    return {"class":field("Class"),"machine":field("Machine"),"type":field("Type"),
            "build_id":m.group(1) if m else None,
            "needed":re.findall(r"Shared library: \[(.*?)\]",d)}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--extracted-root",type=Path,required=True)
    p.add_argument("--dump-root",type=Path,required=True)
    p.add_argument("--json",type=Path,required=True)
    p.add_argument("--markdown",type=Path,required=True)
    a=p.parse_args(); root=a.extracted_root.resolve(); dumps=a.dump_root.resolve()
    if not root.is_dir() or not dumps.is_dir(): p.error("input roots must exist")
    rels=[
      "files2/files2/vendor/audio.primary.mt8163.so",
      "files2/files2/vendor/android.hardware.audio@4.0-impl-mediatek.so",
      "lib/lib/libaudioflinger.so","lib/lib/libaudiopolicymanagerdefault.so",
      "lib/lib/libcarservices_jni.so",
      "vendor_lib/lib/libaudiocomponentengine_vendor.so",
      "vendor_lib/lib/libaudiocustparam_vendor.so","vendor_lib/lib/libaudiosetting.so",
      "vendor_lib/lib/libaudiotoolkit_vendor.so",
      "vendor_lib/lib/modules/cd3313.ko","vendor_lib/lib/modules/ak7604.ko",
      "vendor_lib/lib/modules/fy7604.ko","vendor_lib/lib/modules/carstatus.ko"]
    binaries=[]; clients=[]
    for rel in rels:
        f=root/rel
        if not f.is_file(): continue
        st=cmd(["strings","-a",str(f)]).splitlines()
        hits=[x for x in st if any(k in x.lower() for k in
              ["/dev/audiomux","/dev/carstatus","audiomux_misc_device","extaudiomuxer",
               "sendcmdaudiomux","unable to register misc device"])]
        rec={"path":rel,"size":f.stat().st_size,"sha256":digest(f),"elf":elf(f),"audiomux_strings":hits[:30]}
        binaries.append(rec)
        if hits: clients.append({"path":rel,"matches":hits[:30]})
    standalone=dumps/"kernel/cd3313.ko"; archive=root/"vendor_lib/lib/modules/cd3313.ko"
    comparison=None
    if standalone.is_file() and archive.is_file():
        comparison={"standalone":{"size":standalone.stat().st_size,"sha256":digest(standalone),"elf":elf(standalone)},
                    "vendor_lib":{"size":archive.stat().st_size,"sha256":digest(archive),"elf":elf(archive)},
                    "same_bytes":digest(standalone)==digest(archive)}
        variants=a.json.parent/"module-variants"; variants.mkdir(parents=True,exist_ok=True)
        shutil.copy2(standalone,variants/"cd3313-standalone-dump.ko")
        shutil.copy2(archive,variants/"cd3313-vendor-lib.ko")
        comparison["artifact_copies"]=["module-variants/cd3313-standalone-dump.ko","module-variants/cd3313-vendor-lib.ko"]
    policies=[]
    for rel in ["files2/files2/vendor/audio_policy_configuration.xml",
                "files2/files2/system/audio_policy_configuration.xml"]:
        f=root/rel
        if not f.is_file(): continue
        x=ET.parse(f).getroot(); includes=[]; bad=[]
        for i in x.findall(".//{http://www.w3.org/2001/XInclude}include"):
            q=f.parent/i.get("href",""); includes.append({"href":i.get("href"),"exists":q.is_file()})
        for d in x.findall(".//devicePort"):
            if d.get("role")=="source":
                for prof in d.findall("profile"):
                    mask=prof.get("channelMasks","")
                    if "AUDIO_CHANNEL_OUT_" in mask:
                        bad.append({"port":d.get("tagName"),"mask":mask})
        sco=[]
        for d in x.findall(".//devicePort"):
            if d.get("tagName")=="BT SCO Headset Mic":
                sco=[{"role":d.get("role"),"type":d.get("type"),
                      "profiles":[{"rates":z.get("samplingRates"),"mask":z.get("channelMasks")} for z in d.findall("profile")]}]
        policies.append({"path":rel,"bt_sco_headset_mic":sco,"missing_includes":[z["href"] for z in includes if not z["exists"]],
                         "input_output_mask_mismatches":bad})
    mixer=root/"files2/files2/vendor/audio_device.xml"; mixer_info=None
    if mixer.is_file():
        x=ET.parse(mixer).getroot(); stray=[]; dup=[]
        for path in x.findall("path"):
            t="".join(path.itertext())
            if t.strip(): stray.append({"path":path.get("name"),"value":path.get("value"),"text":t})
            ctrls=[(k.get("name"),k.get("value")) for k in path.findall("kctl")]
            if len(ctrls)!=len(set(ctrls)): dup.append({"path":path.get("name"),"value":path.get("value"),"controls":ctrls})
        mixer_info={"stray_text_paths":stray,"duplicate_control_paths":dup}
    init={}
    for name in ["init.mt8163.rc","factory_init.rc"]:
        f=dumps/name
        if f.is_file():
            t=f.read_text(encoding="utf-8",errors="replace")
            init[name]={"dsp_insmod_lines":[z.strip() for z in t.splitlines() if "insmod" in z and any(k in z.lower() for k in ["cd3313","ak7604","fy7604","carstatus"])],
                        "ak7604_gain_fallbacks":re.findall(r"ro\.hw\.ak7604\.gain:\s*([^}]+)",t),
                        "has_dsp_chip_property":"ro.hw.dsp.chip" in t}
    props={}
    for name in ["build.prop","default.prop"]:
        f=dumps/name
        if f.is_file(): props[name]=[z for z in f.read_text(encoding="utf-8",errors="replace").splitlines() if "ro.hw.dsp.chip" in z]
    firmware_images=[]
    image_dir=a.json.parent/"firmware-images"; image_dir.mkdir(parents=True,exist_ok=True)
    for name in ["boot.img","dtbo.img"]:
        source=dumps/name
        if source.is_file():
            target=image_dir/name; shutil.copy2(source,target)
            hits=[z for z in cmd(["strings","-a",str(source)]).splitlines()
                  if any(k in z.lower() for k in ["cd3313","ak7604","fy7604","audiomux","i2c","mediatek,audio","audio-dsp"])]
            firmware_images.append({"name":name,"size":source.stat().st_size,"sha256":digest(source),
                                    "strings_hits":hits[:200],"artifact_copy":"firmware-images/"+name})
    data={"schema_version":1,"generated_at_utc":datetime.now(timezone.utc).isoformat(),
          "binaries":binaries,"audiomux_clients":clients,"cd3313_comparison":comparison,
          "audio_policy":policies,"audio_device_xml":mixer_info,"init_module_loading":init,
          "dsp_chip_property_in_build_props":props,"firmware_images":firmware_images}
    a.json.parent.mkdir(parents=True,exist_ok=True); a.markdown.parent.mkdir(parents=True,exist_ok=True)
    a.json.write_text(json.dumps(data,indent=2,ensure_ascii=False,sort_keys=True)+"\n",encoding="utf-8")
    lines=["# MT8163 audio stack inventory","",f"Generated: {data['generated_at_utc']}","","## Binaries","",
           "| File | Bytes | ELF class | Machine | Build ID | SHA-256 |","|---|---:|---|---|---|---|"]
    for b in binaries:
        e=b["elf"]; lines.append(f"| {b['path']} | {b['size']} | {e['class']} | {e['machine']} | {e['build_id']} | {b['sha256']} |")
    lines += ["","## /dev/audiomux clients",""]
    for c in clients: lines.append("- "+c["path"]+": "+"; ".join(c["matches"]))
    if comparison:
        lines += ["","## CD3313 module comparison","",
          f"- Standalone dump: {comparison['standalone']['size']} bytes; SHA-256 {comparison['standalone']['sha256']}; Build ID {comparison['standalone']['elf']['build_id']}",
          f"- vendor_lib archive: {comparison['vendor_lib']['size']} bytes; SHA-256 {comparison['vendor_lib']['sha256']}; Build ID {comparison['vendor_lib']['elf']['build_id']}",
          f"- Same bytes: {comparison['same_bytes']}"]
    lines += ["","## AudioPolicy and mixer XML",""]
    for q in policies: lines.append(f"- {q['path']}: missing includes={q['missing_includes']}; input/output mask mismatches={q['input_output_mask_mismatches']}")
    if mixer_info: lines.append(f"- audio_device.xml: {len(mixer_info['stray_text_paths'])} paths with stray text; {len(mixer_info['duplicate_control_paths'])} paths with duplicate controls")
    lines += ["","## Firmware image string scan",""]
    for q in firmware_images: lines.append("- {}: {} bytes; SHA-256 {}; matches: {}".format(q["name"],q["size"],q["sha256"],q["strings_hits"]))
    lines += ["","## DSP module loading",""]
    for name,q in init.items():
        lines.append(f"### {name}")
        lines += ["- "+z for z in q["dsp_insmod_lines"]]
        lines.append("- AK7604 gain fallbacks: "+str(q["ak7604_gain_fallbacks"]))
    lines += ["","Static analysis only; this report does not establish which I2C device probes or which DSP is physically fitted.",""]
    a.markdown.write_text("\n".join(lines),encoding="utf-8")
    print(f"Analyzed {len(binaries)} binaries and found {len(clients)} audiomux-related files.")
    return 0
if __name__=="__main__": raise SystemExit(main())
