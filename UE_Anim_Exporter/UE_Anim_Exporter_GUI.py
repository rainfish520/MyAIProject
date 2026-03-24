# UE动画批量导出工具 - GUI版本 v1.8
# 新增: 添加移动文件按钮

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import subprocess
import os
import json
import psutil
import threading
import shutil

VERSION = "1.8.0"

DEFAULT_EXCLUDE = [
    "ALS_N_Lean",
    "ALS_N_Lean_Falling",
    "ALS_N_Look",
    "ALS_N_WalkRun_B",
    "ALS_N_WalkRun_BL",
    "ALS_N_WalkRun_BR",
    "ALS_N_WalkRun_F",
    "ALS_N_WalkRun_FL",
    "ALS_N_WalkRun_FR",
]


class UEDetector:
    @staticmethod
    def find_running_ue_instances():
        running_ues = []
        ue_exe_names = ["UnrealEditor.exe", "UnrealEditor-Cmd.exe"]
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] in ue_exe_names:
                    cmdline = proc.info.get('cmdline', [])
                    project_path = ""
                    for arg in cmdline:
                        if arg.endswith('.uproject'):
                            project_path = arg
                            break
                    running_ues.append({'pid': proc.info['pid'], 'name': proc.info['name'], 'project': project_path})
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return running_ues


class UEAnimExporterApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"UE动画批量导出工具 v{VERSION}")
        self.root.geometry("900x750")
        self.root.minsize(800, 600)

        self.project_path = tk.StringVar()
        self.export_path = tk.StringVar(value="H:/BBC_About/FBX_Export/")
        self.ue_path = tk.StringVar()
        self.content_root = tk.StringVar(value="H:/BBC_5.7/Content")
        self.found_animations = []
        
        # 导出模式: "flat"=扁平化, "keep"=保持原目录
        self.export_mode = tk.StringVar(value="flat")
        
        self.detect_ue_path()
        self.create_widgets()
        self.load_config()
        self.root.after(500, self.check_ue_status)

    def detect_ue_path(self):
        common_paths = [
            r"C:\Program Files\Epic Games\UE_5.4\Engine\Binaries\Win64\UnrealEditor.exe",
            r"C:\Program Files\Epic Games\UE_5.3\Engine\Binaries\Win64\UnrealEditor.exe",
            r"C:\Program Files\Epic Games\UE_5.2\Engine\Binaries\Win64\UnrealEditor.exe",
            r"C:\Program Files\Epic Games\UE_5.1\Engine\Binaries\Win64\UnrealEditor.exe",
            r"C:\Program Files\Epic Games\UE_5.0\Engine\Binaries\Win64\UnrealEditor.exe",
            r"F:\Program Files\Epic Games\UE_5.7\Engine\Binaries\Win64\UnrealEditor.exe",
        ]
        for path in common_paths:
            if os.path.exists(path):
                self.ue_path.set(path)
                return
        self.ue_path.set("")

    def create_widgets(self):
        self.canvas = tk.Canvas(self.root, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        def on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.canvas.bind_all("<MouseWheel>", on_mousewheel)
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", on_mousewheel))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        main_frame = ttk.Frame(self.scrollable_frame, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # UE状态
        status_frame = ttk.LabelFrame(main_frame, text="UE编辑器状态", padding="5")
        status_frame.pack(fill=tk.X, pady=(0, 5))

        status_container = ttk.Frame(status_frame)
        status_container.pack(fill=tk.X)

        self.status_indicator = tk.Canvas(status_container, width=16, height=16)
        self.status_indicator.pack(side=tk.LEFT, padx=(0, 8))
        self.status_circle = self.status_indicator.create_oval(2, 2, 14, 14, fill="gray")

        self.status_label = ttk.Label(status_container, text="正在检测...", font=("Segoe UI", 9))
        self.status_label.pack(side=tk.LEFT)
        ttk.Button(status_container, text="刷新", command=self.check_ue_status).pack(side=tk.RIGHT)

        self.ue_list_label = ttk.Label(status_container, text="", font=("Segoe UI", 8), foreground="blue")
        self.ue_list_label.pack(side=tk.LEFT, padx=10)

        # 项目设置
        project_frame = ttk.LabelFrame(main_frame, text="项目设置", padding="5")
        project_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(project_frame, text="UE项目:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(project_frame, textvariable=self.project_path, width=55).grid(row=0, column=1, padx=5)
        ttk.Button(project_frame, text="浏览", command=self.browse_project).grid(row=0, column=2, pady=2)

        ttk.Label(project_frame, text="UE编辑器:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(project_frame, textvariable=self.ue_path, width=55).grid(row=1, column=1, padx=5)
        ttk.Button(project_frame, text="浏览", command=self.browse_ue).grid(row=1, column=2, pady=2)

        # 扫描设置
        scan_frame = ttk.LabelFrame(main_frame, text="扫描设置", padding="5")
        scan_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(scan_frame, text="Content目录:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(scan_frame, textvariable=self.content_root, width=55).grid(row=0, column=1, padx=5)
        ttk.Button(scan_frame, text="浏览", command=self.browse_content).grid(row=0, column=2, pady=2)

        ttk.Label(scan_frame, text="相对路径:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.ue_content_entry = ttk.Entry(scan_frame, width=50)
        self.ue_content_entry.insert(0, "AdvancedLocomotionV4/CharacterAssets/MannequinSkeleton/AnimationExamples")
        self.ue_content_entry.grid(row=1, column=1, padx=5, sticky=tk.W)
        ttk.Button(scan_frame, text="浏览", command=self.browse_relative_path).grid(row=1, column=2, pady=2)

        # 导出设置
        export_frame = ttk.LabelFrame(main_frame, text="导出设置", padding="5")
        export_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(export_frame, text="导出目录:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(export_frame, textvariable=self.export_path, width=55).grid(row=0, column=1, padx=5)
        ttk.Button(export_frame, text="浏览", command=self.browse_export_path).grid(row=0, column=2, pady=2)

        # 导出模式选择
        mode_frame = ttk.Frame(export_frame)
        mode_frame.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        ttk.Label(mode_frame, text="导出模式:").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(mode_frame, text="保持原目录结构", variable=self.export_mode, value="keep").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="全部放在根目录", variable=self.export_mode, value="flat").pack(side=tk.LEFT, padx=5)

        # 动画列表
        list_frame = ttk.LabelFrame(main_frame, text="动画列表", padding="5")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        toolbar = ttk.Frame(list_frame)
        toolbar.pack(fill=tk.X, pady=(0, 3))

        ttk.Button(toolbar, text="全选", command=self.select_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="取消", command=self.deselect_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="扫描", command=self.scan_animations).pack(side=tk.LEFT, padx=2)

        list_container = ttk.Frame(list_frame)
        list_container.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.anim_listbox = tk.Listbox(list_container, selectmode=tk.EXTENDED, yscrollcommand=scrollbar.set,
                                       font=("Consolas", 9), height=8)
        self.anim_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.anim_listbox.yview)

        self.list_info = ttk.Label(list_frame, text="点击扫描获取动画列表")
        self.list_info.pack()

        # 排除列表
        exclude_frame = ttk.LabelFrame(main_frame, text="排除列表", padding="5")
        exclude_frame.pack(fill=tk.X, pady=(0, 5))

        self.exclude_text = scrolledtext.ScrolledText(exclude_frame, height=2, font=("Consolas", 8))
        self.exclude_text.pack(fill=tk.X)
        self.exclude_text.insert("1.0", "\n".join(DEFAULT_EXCLUDE))

        # 日志
        log_frame = ttk.LabelFrame(main_frame, text="日志", padding="5")
        log_frame.pack(fill=tk.X, pady=(0, 5))

        self.log_text = scrolledtext.ScrolledText(log_frame, height=5, font=("Consolas", 8))
        self.log_text.pack(fill=tk.X)

        # 导出进度标签
        self.export_progress_label = ttk.Label(main_frame, text="", font=("Segoe UI", 9))
        self.export_progress_label.pack(pady=(0, 5))

        # 按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(5, 0))

        self.scan_btn = ttk.Button(button_frame, text="扫描动画资产", command=self.scan_animations)
        self.scan_btn.pack(side=tk.LEFT, padx=5)

        self.export_btn = ttk.Button(button_frame, text="导出选中动画", command=self.start_export, style="Accent.TButton")
        self.export_btn.pack(side=tk.LEFT, padx=5)

        self.copy_script_btn = ttk.Button(button_frame, text="复制导出脚本", command=self.copy_export_script)
        self.copy_script_btn.pack(side=tk.LEFT, padx=5)

        # 新增：移动文件按钮
        self.move_btn = ttk.Button(button_frame, text="整理文件到根目录", command=self.move_files_to_root)
        self.move_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="清空", command=self.clear_log).pack(side=tk.LEFT, padx=5)

        self.progress = ttk.Progressbar(button_frame, mode='determinate', length=150)
        self.progress.pack(side=tk.RIGHT, padx=5)

        style = ttk.Style()
        style.configure("Accent.TButton", font=("Segoe UI", 9, "bold"))

    def check_ue_status(self):
        running_ues = UEDetector.find_running_ue_instances()
        if running_ues:
            self.status_indicator.itemconfig(self.status_circle, fill="green")
            self.status_label.config(text=f"UE运行中 ({len(running_ues)})")
            if len(running_ues) == 1:
                proj = os.path.basename(running_ues[0]['project']) or "未加载"
                self.ue_list_label.config(text=f"{proj}")
            else:
                projs = [os.path.basename(ue['project']) or "未加载" for ue in running_ues]
                self.ue_list_label.config(text=f"多个: {', '.join(projs[:2])}")
        else:
            self.status_indicator.itemconfig(self.status_circle, fill="gray")
            self.status_label.config(text="UE未运行")
            self.ue_list_label.config(text="")

    def browse_project(self):
        path = filedialog.askopenfilename(title="选择UE项目", filetypes=[("UE Project", "*.uproject")], initialdir="H:/")
        if path:
            self.project_path.set(path)
            project_dir = os.path.dirname(path)
            content_dir = os.path.join(project_dir, "Content")
            if os.path.exists(content_dir):
                self.content_root.set(content_dir.replace("\\", "/"))
            self.log(f"项目: {os.path.basename(path)}")

    def browse_ue(self):
        path = filedialog.askopenfilename(title="选择UE编辑器", filetypes=[("Executable", "*.exe")], initialdir=r"C:\Program Files\Epic Games")
        if path:
            self.ue_path.set(path)
            self.log(f"UE: {os.path.basename(os.path.dirname(os.path.dirname(path)))}")

    def browse_content(self):
        path = filedialog.askdirectory(title="选择Content目录", initialdir="H:/BBC_5.7")
        if path:
            self.content_root.set(path.replace("\\", "/"))
            self.log(f"Content: {path}")

    def browse_relative_path(self):
        content_root = self.content_root.get().strip()
        if not content_root or not os.path.exists(content_root):
            messagebox.showwarning("警告", "请先选择有效的Content目录！")
            return
        
        path = filedialog.askdirectory(title="选择动画资源目录(相对于Content)", initialdir=content_root)
        if path:
            rel_path = path.replace(content_root, "").strip("/")
            self.ue_content_entry.delete(0, tk.END)
            self.ue_content_entry.insert(0, rel_path)
            self.log(f"相对路径: {rel_path}")

    def browse_export_path(self):
        path = filedialog.askdirectory(title="选择导出目录", initialdir="H:/BBC_About")
        if path:
            self.export_path.set(path.replace("\\", "/"))
            self.log(f"导出目录: {path}")

    def log(self, message):
        self.log_text.insert(tk.END, f"[{self.get_time()}] {message}\n")
        self.log_text.see(tk.END)

    def get_time(self):
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")

    def clear_log(self):
        self.log_text.delete(1.0, tk.END)

    def get_exclude_list(self):
        text = self.exclude_text.get(1.0, tk.END)
        return [line.strip() for line in text.split("\n") if line.strip()]

    def scan_animations(self):
        content_root = self.content_root.get().strip()
        ue_content_path = self.ue_content_entry.get().strip()

        if not content_root or not os.path.exists(content_root):
            messagebox.showwarning("警告", "请选择有效的Content目录！")
            return

        self.log("=" * 40)
        self.log("开始扫描...")
        self.scan_btn.config(state="disabled")
        self.anim_listbox.delete(0, tk.END)
        self.list_info.config(text="扫描中...")

        thread = threading.Thread(target=self._scan_filesystem, args=(content_root, ue_content_path))
        thread.start()

    def _scan_filesystem(self, content_root, ue_content_path):
        try:
            content_root = content_root.replace("\\", "/")
            ue_content_path = ue_content_path.replace("\\", "/")
            full_path = content_root + "/" + ue_content_path

            self.root.after(0, lambda: self.log(f"扫描: {full_path}"))

            if not os.path.exists(full_path):
                self.root.after(0, lambda: self.log(f"目录不存在: {full_path}"))
                self.root.after(0, lambda: self.list_info.config(text="路径不存在！"))
                self.root.after(0, lambda: self.scan_btn.config(state="normal"))
                return

            animations = []
            
            for root, dirs, files in os.walk(full_path):
                for file in files:
                    if file.endswith(".uasset"):
                        anim_name = file.replace(".uasset", "")
                        if anim_name not in animations:
                            animations.append(anim_name)

            self.found_animations = sorted(animations)
            exclude_list = self.get_exclude_list()
            self.root.after(0, lambda: self.anim_listbox.delete(0, tk.END))

            count = 0
            for anim in self.found_animations:
                if anim not in exclude_list:
                    self.root.after(0, lambda a=anim: self.anim_listbox.insert(tk.END, f"  {a}"))
                    count += 1

            self.root.after(0, lambda c=count, t=len(self.found_animations), e=len(exclude_list):
                self.list_info.config(text=f"共{t}个, 可导出{c}个 (排除{e}个)"))
            self.root.after(0, lambda: self.log(f"完成! 找到{len(self.found_animations)}个"))

        except Exception as e:
            self.root.after(0, lambda: self.log(f"异常: {str(e)}"))
        finally:
            self.root.after(0, lambda: self.scan_btn.config(state="normal"))

    def select_all(self):
        self.anim_listbox.select_set(0, tk.END)

    def deselect_all(self):
        self.anim_listbox.selection_clear(0, tk.END)

    def get_selected_animations(self):
        return [self.anim_listbox.get(i).strip() for i in self.anim_listbox.curselection()]

    def move_files_to_root(self):
        """移动导出目录中的所有FBX文件到根目录"""
        export_dir = self.export_path.get().strip()
        # 统一为反斜杠格式
        export_dir = export_dir.replace("/", "\\")
        
        if not export_dir or not os.path.exists(export_dir):
            messagebox.showwarning("警告", "导出目录不存在！")
            return
        
        self.log("=" * 50)
        self.log(f"开始整理文件...")
        self.log(f"导出目录: {export_dir}")
        
        moved_count = 0
        failed_count = 0
        skipped_count = 0
        
        try:
            # 遍历所有子目录
            for root, dirs, files in os.walk(export_dir):
                # 统一root为反斜杠格式
                root_normalized = root.replace("/", "\\")
                
                for file in files:
                    if file.lower().endswith(".fbx"):
                        src_path = os.path.join(root, file)
                        dst_path = os.path.join(export_dir, file)
                        
                        # 如果已经在根目录，跳过
                        if root_normalized.lower() == export_dir.lower():
                            skipped_count += 1
                            continue
                        
                        # 如果目标文件已存在，先删除
                        if os.path.exists(dst_path):
                            try:
                                os.remove(dst_path)
                            except:
                                pass
                        
                        try:
                            # 移动文件
                            shutil.move(src_path, dst_path)
                            moved_count += 1
                            self.log(f"移动: {file}")
                        except Exception as e:
                            failed_count += 1
                            self.log(f"移动失败: {file} - {str(e)}")
            
            # 清理空目录
            self._cleanup_empty_dirs(export_dir)
            
            self.log(f"整理完成！")
            self.log(f"移动: {moved_count} 个")
            self.log(f"跳过: {skipped_count} 个")
            self.log(f"失败: {failed_count} 个")
            
            messagebox.showinfo("整理完成", 
                f"文件整理完成！\n\n"
                f"移动: {moved_count} 个\n"
                f"跳过: {skipped_count} 个\n"
                f"失败: {failed_count} 个\n\n"
                f"所有FBX文件已移动到根目录。")
                
        except Exception as e:
            self.log(f"整理异常: {str(e)}")
            messagebox.showerror("错误", f"整理文件时出错: {str(e)}")

    def _cleanup_empty_dirs(self, directory):
        """清理空目录"""
        for root, dirs, files in os.walk(directory, topdown=False):
            for d in dirs:
                dir_path = os.path.join(root, d)
                # 不删除根目录
                if dir_path != directory:
                    try:
                        if not os.listdir(dir_path):  # 如果目录为空
                            os.rmdir(dir_path)
                    except:
                        pass

    def generate_export_script(self):
        """生成导出脚本"""
        selected = self.get_selected_animations()
        mode = self.export_mode.get()  # "flat" or "keep"
        
        ue_content = self.ue_content_entry.get().strip().replace("\\", "/")
        if not ue_content.startswith("/Game/"):
            if ue_content.startswith("/"):
                ue_content = "/Game" + ue_content
            else:
                ue_content = "/Game/" + ue_content
        export_path = self.export_path.get().replace("\\", "/")

        # 构建导出脚本
        script = f'''import unreal
import os
import shutil

animations_to_export = {selected}
export_destination = r"{export_path}"
ue_base_path = "{ue_content}"
export_mode = "{mode}"

os.makedirs(export_destination, exist_ok=True)

print(f"开始导出 {{len(animations_to_export)}} 个动画...")
print(f"导出模式: {{'保持原目录' if export_mode == 'keep' else '扁平化到根目录'}}")
print(f"导出目录: {{export_destination}}")

# 获取ue_base_path下所有资产
all_assets = unreal.EditorAssetLibrary.list_assets(ue_base_path, True)
print(f"找到 {{len(all_assets)}} 个资产")

# 临时文件夹用于UE导出
temp_folder = os.path.join(export_destination, "_ue_temp_export")
os.makedirs(temp_folder, exist_ok=True)

success_count = 0
failed_count = 0
failed_list = []

for i, anim_name in enumerate(animations_to_export):
    print(f"[{{i+1}}/{{len(animations_to_export)}}] {{anim_name}}...")
    
    # 查找匹配的资产
    asset_path = None
    asset_relative_path = ""
    for asset in all_assets:
        if anim_name in asset and asset.endswith("." + anim_name):
            asset_path = asset
            if asset.startswith(ue_base_path):
                asset_relative_path = asset[len(ue_base_path):].strip("/")
                if "/" in asset_relative_path:
                    asset_relative_path = "/".join(asset_relative_path.split("/")[:-1])
            break
    
    if not asset_path:
        print(f"  NOT_FOUND: {{anim_name}}")
        failed_count += 1
        failed_list.append(anim_name)
        continue
    
    # 清空临时文件夹
    for f in os.listdir(temp_folder):
        fp = os.path.join(temp_folder, f)
        if os.path.isfile(fp):
            os.remove(fp)
    
    # 使用UE导出
    unreal.AssetToolsHelpers.get_asset_tools().export_assets([asset_path], temp_folder)
    
    # 查找导出的FBX文件
    exported_files = [f for f in os.listdir(temp_folder) if f.endswith(".fbx")]
    
    if not exported_files:
        print(f"  失败: {{anim_name}} (未导出FBX)")
        failed_count += 1
        failed_list.append(anim_name)
        continue
    
    # 确定最终目标路径
    fbx_filename = anim_name + ".fbx"
    final_path = os.path.join(export_destination, fbx_filename)
    
    if export_mode == "flat":
        # 扁平化模式: 使用实际导出的文件名移动到根目录
        if os.path.exists(final_path):
            os.remove(final_path)
        actual_filename = exported_files[0]
        shutil.move(os.path.join(temp_folder, actual_filename), final_path)
        print(f"  成功: {{fbx_filename}}")
        success_count += 1
    else:
        # 保持结构模式
        if asset_relative_path:
            target_dir = os.path.join(export_destination, asset_relative_path.replace("/", os.sep))
            os.makedirs(target_dir, exist_ok=True)
            target_path = os.path.join(target_dir, fbx_filename)
        else:
            target_path = final_path
        
        if os.path.exists(target_path):
            os.remove(target_path)
        actual_filename = exported_files[0]
        shutil.move(os.path.join(temp_folder, actual_filename), target_path)
        print(f"  成功: {{fbx_filename}}")
        success_count += 1

# 清理临时文件夹
if os.path.exists(temp_folder):
    for f in os.listdir(temp_folder):
        fp = os.path.join(temp_folder, f)
        if os.path.isfile(fp):
            os.remove(fp)
    if not os.listdir(temp_folder):
        os.rmdir(temp_folder)

print(f"")
print(f"===== 导出完成 =====")
print(f"成功: {{success_count}} 个")
print(f"失败: {{failed_count}} 个")
if failed_list:
    print(f"失败列表: {{', '.join(failed_list)}}")
'''

        return script

    def copy_export_script(self):
        """复制导出脚本到剪贴板"""
        selected = self.get_selected_animations()
        if not selected:
            messagebox.showwarning("警告", "请先扫描并选择动画！")
            return

        mode = self.export_mode.get()
        mode_desc = "保持原目录结构" if mode == "keep" else "扁平化到根目录"

        script = self.generate_export_script()
        self.root.clipboard_clear()
        self.root.clipboard_append(script)
        
        self.log("=" * 50)
        self.log(f"导出模式: {mode_desc}")
        self.log(f"将导出 {len(selected)} 个动画")
        self.log("导出脚本已复制到剪贴板！")
        self.log("请在UE编辑器中:")
        self.log("1. 打开项目")
        self.log("2. 菜单: Window -> Developer Tools -> Output Log")
        self.log("3. 底部切换到 Python 标签")
        self.log("4. 粘贴并回车执行")
        self.log("=" * 50)
        
        messagebox.showinfo("复制成功", 
            f"导出脚本已复制到剪贴板！\n\n"
            f"导出模式: {mode_desc}\n"
            f"动画数量: {len(selected)} 个\n\n"
            f"请在UE编辑器中:\n"
            f"1. 打开BBC_5.7项目\n"
            f"2. Window -> Developer Tools -> Output Log\n"
            f"3. 底部切换到 Python 标签\n"
            f"4. 粘贴并回车执行")

    def start_export(self):
        """通过UE编辑器导出"""
        selected = self.get_selected_animations()
        if not selected:
            messagebox.showwarning("警告", "请先扫描并选择动画！")
            return

        ue_path = self.ue_path.get()
        if not ue_path or not os.path.exists(ue_path):
            messagebox.showwarning("警告", "UE编辑器路径无效！\n\n建议使用'复制导出脚本'方式，在已打开的UE中执行。")
            return

        mode = self.export_mode.get()
        mode_desc = "保持原目录结构" if mode == "keep" else "扁平化到根目录"

        if not messagebox.askyesno("确认", 
            f"将通过UE编辑器导出 {len(selected)} 个动画。\n\n"
            f"导出模式: {mode_desc}\n"
            f"导出目录: {self.export_path.get()}\n\n"
            f"注意: UE启动可能需要2-5分钟。\n"
            f"如果已打开UE，建议使用'复制导出脚本'方式。\n\n继续？"):
            return

        self.log("=" * 50)
        self.log(f"开始导出 {len(selected)} 个动画...")
        self.log(f"导出模式: {mode_desc}")
        self.log("提示: UE启动可能需要2-5分钟，请耐心等待")
        self.log("=" * 50)

        script = self.generate_export_script()
        script_path = "H:/BBC_About/UE_Anim_Exporter/temp_export.py"
        os.makedirs(os.path.dirname(script_path), exist_ok=True)
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script)

        self.scan_btn.config(state="disabled")
        self.export_btn.config(state="disabled")
        self.copy_script_btn.config(state="disabled")
        self.move_btn.config(state="disabled")
        self.progress["maximum"] = len(selected)
        self.progress["value"] = 0
        self.export_progress_label.config(text=f"进度: 0/{len(selected)}")

        thread = threading.Thread(target=self._export_thread, args=(script_path, selected))
        thread.start()

    def _export_thread(self, script_path, animations):
        try:
            cmd = f'"{self.ue_path.get()}" "{self.project_path.get()}" -RunPythonScript="{script_path}" -stdout -nullrhi -NoSplash'
            self.root.after(0, lambda: self.log("正在启动UE编辑器..."))
            self.root.after(0, lambda: self.log("这可能需要2-5分钟..."))

            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            output_lines = []
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    decoded = line.decode("utf-8", errors="ignore").strip()
                    if decoded:
                        output_lines.append(decoded)
                        if decoded.startswith("["):
                            self.root.after(0, lambda d=decoded: self.log(d))

            stdout, stderr = process.communicate()

            output = "\n".join(output_lines)
            
            # 解析结果
            success = output.count("成功:")
            failed = output.count("失败:")
            
            self.root.after(0, lambda: self.progress.config(value=len(animations)))
            self.root.after(0, lambda: self.export_progress_label.config(text=f"完成! 成功:{success}, 失败:{failed}"))
            self.root.after(0, lambda: self.log(f"导出完成! 成功:{success}, 失败:{failed}"))

            if stderr:
                err = stderr.decode("utf-8", errors="ignore")
                if err.strip():
                    self.root.after(0, lambda: self.log(f"UE错误: {err[:200]}"))

        except subprocess.TimeoutExpired:
            self.root.after(0, lambda: self.log("导出超时(10分钟)!"))
            process.kill()
        except Exception as e:
            self.root.after(0, lambda: self.log(f"异常: {str(e)}"))
        finally:
            if os.path.exists(script_path):
                os.remove(script_path)
            self.root.after(0, lambda: self.scan_btn.config(state="normal"))
            self.root.after(0, lambda: self.export_btn.config(state="normal"))
            self.root.after(0, lambda: self.copy_script_btn.config(state="normal"))
            self.root.after(0, lambda: self.move_btn.config(state="normal"))
            
            # 导出完成弹框
            self.root.after(0, lambda: messagebox.showinfo("导出完成", 
                f"导出任务已完成！\n\n"
                f"成功: {success} 个\n"
                f"失败: {failed} 个\n\n"
                f"导出目录: {self.export_path.get()}\n\n"
                f"提示: 可以点击'整理文件到根目录'将分散的文件移动到根目录。"))

    def load_config(self):
        config_file = "H:/BBC_About/UE_Anim_Exporter/config.json"
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    if config.get("project_path"):
                        self.project_path.set(config["project_path"])
                    if config.get("export_path"):
                        self.export_path.set(config["export_path"])
                    if config.get("ue_editor_path"):
                        self.ue_path.set(config["ue_editor_path"])
                    if config.get("content_root"):
                        self.content_root.set(config["content_root"])
                    if config.get("export_mode"):
                        self.export_mode.set(config["export_mode"])
            except:
                pass

    def save_config(self):
        config_file = "H:/BBC_About/UE_Anim_Exporter/config.json"
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        try:
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump({
                    "project_path": self.project_path.get(),
                    "export_path": self.export_path.get(),
                    "ue_editor_path": self.ue_path.get(),
                    "content_root": self.content_root.get(),
                    "export_mode": self.export_mode.get(),
                }, f, ensure_ascii=False, indent=2)
        except:
            pass

    def on_closing(self):
        self.save_config()
        self.canvas.unbind_all("<MouseWheel>")
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = UEAnimExporterApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
