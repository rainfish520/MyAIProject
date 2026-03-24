import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import xml.etree.ElementTree as ET
import os
import re
import copy

class EffectAddressReplacer:
    def __init__(self, root):
        self.root = root
        self.root.title("特效挂接批量替换工具")
        self.root.geometry("1400x750")

        # === 单文件模式数据 ===
        self.file_path = ""
        self.tree = None
        self.effect_addresses = []  # 存储所有特效地址
        self.address_entries = []  # 存储右侧输入框
        self.initial_addresses = []  # 存储初始地址（用于还原）

        # === 对比模式数据 ===
        self.source_tree = None
        self.target_tree = None
        self.compare_results = []  # [{source, target, status}, ...]
        self.compare_entries = []  # [{entry_var, target_cue, status}, ...]
        self.compare_right_frames = []  # 存储右侧frame引用，用于就地更新

        self.setup_ui()

    def setup_ui(self):
        # 创建选项卡
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=(5, 0))

        # 选项卡1：单文件模式
        self.single_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.single_tab, text="  单文件模式  ")
        self.setup_single_mode(self.single_tab)

        # 选项卡2：对比模式
        self.compare_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.compare_tab, text="  对比模式  ")
        self.setup_compare_mode(self.compare_tab)

        # 统一鼠标滚轮绑定
        self.root.bind_all("<MouseWheel>", self._on_mousewheel)

        # 共享状态栏
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN).pack(fill=tk.X, padx=10, pady=5)

    def _on_mousewheel(self, event):
        """根据当前选项卡滚动对应的Canvas"""
        try:
            current_tab = self.notebook.index(self.notebook.select())
            if current_tab == 0:
                self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            elif current_tab == 1:
                self.compare_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass

    # ================================================================
    #  单文件模式 UI
    # ================================================================

    def setup_single_mode(self, parent):
        """设置单文件模式UI（原有功能）"""
        # 顶部文件选择区域
        top_frame = ttk.Frame(parent, padding="10")
        top_frame.pack(fill=tk.X)

        ttk.Label(top_frame, text="选择.graph文件:").pack(side=tk.LEFT)
        self.file_path_var = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.file_path_var, width=60).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="浏览...", command=self.browse_file).pack(side=tk.LEFT)
        ttk.Button(top_frame, text="解析文件", command=self.parse_file).pack(side=tk.LEFT, padx=5)

        # 主内容区域
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 创建表头
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 5))

        left_header = ttk.Label(header_frame, text="原始特效地址", font=("Arial", 10, "bold"))
        left_header.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        right_header = ttk.Label(header_frame, text="新特效地址（可编辑）", font=("Arial", 10, "bold"))
        right_header.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        # 创建带滚动条的容器
        container = ttk.Frame(main_frame)
        container.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(container)
        scrollbar_y = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        scrollbar_x = ttk.Scrollbar(container, orient="horizontal", command=self.canvas.xview)

        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")

        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.scrollable_frame.grid_columnconfigure(0, weight=1, minsize=500)
        self.scrollable_frame.grid_columnconfigure(1, weight=1, minsize=500)

        # 底部按钮区域
        bottom_frame = ttk.Frame(parent, padding="10")
        bottom_frame.pack(fill=tk.X)

        ttk.Button(bottom_frame, text="还原为初始地址", command=self.reset_to_initial).pack(side=tk.LEFT, padx=5)
        ttk.Button(bottom_frame, text="保存修改", command=self.save_file).pack(side=tk.RIGHT, padx=5)
        ttk.Button(bottom_frame, text="另存为...", command=self.save_file_as).pack(side=tk.RIGHT)

    # ================================================================
    #  对比模式 UI
    # ================================================================

    def setup_compare_mode(self, parent):
        """设置对比模式UI"""
        # 文件选择区域
        file_frame = ttk.LabelFrame(parent, text="文件选择", padding="10")
        file_frame.pack(fill=tk.X, padx=10, pady=5)

        # 源文件选择
        source_frame = ttk.Frame(file_frame)
        source_frame.pack(fill=tk.X, pady=2)
        ttk.Label(source_frame, text="源文件(参考):", width=15, anchor=tk.W).pack(side=tk.LEFT)
        self.source_path_var = tk.StringVar()
        ttk.Entry(source_frame, textvariable=self.source_path_var, width=55).pack(side=tk.LEFT, padx=5)
        ttk.Button(source_frame, text="浏览...", command=self.browse_source).pack(side=tk.LEFT)

        # 目标文件选择
        target_frame = ttk.Frame(file_frame)
        target_frame.pack(fill=tk.X, pady=2)
        ttk.Label(target_frame, text="目标文件(修改):", width=15, anchor=tk.W).pack(side=tk.LEFT)
        self.target_path_var = tk.StringVar()
        ttk.Entry(target_frame, textvariable=self.target_path_var, width=55).pack(side=tk.LEFT, padx=5)
        ttk.Button(target_frame, text="浏览...", command=self.browse_target).pack(side=tk.LEFT)

        # 解析按钮行
        btn_frame = ttk.Frame(file_frame)
        btn_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(btn_frame, text="解析对比", command=self.parse_compare).pack(side=tk.LEFT)

        # 统计信息
        self.compare_stats_var = tk.StringVar(value="")
        ttk.Label(btn_frame, textvariable=self.compare_stats_var, foreground="gray").pack(side=tk.LEFT, padx=15)

        # 主内容区域
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 表头
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(header_frame, text="源文件特效地址（参考）", font=("Arial", 10, "bold")).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Label(header_frame, text="目标文件特效地址（可编辑）", font=("Arial", 10, "bold")).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        # 滚动容器
        container = ttk.Frame(main_frame)
        container.pack(fill=tk.BOTH, expand=True)

        self.compare_canvas = tk.Canvas(container)
        cmp_scrollbar_y = ttk.Scrollbar(container, orient="vertical", command=self.compare_canvas.yview)
        cmp_scrollbar_x = ttk.Scrollbar(container, orient="horizontal", command=self.compare_canvas.xview)

        self.compare_scrollable = ttk.Frame(self.compare_canvas)

        self.compare_scrollable.bind(
            "<Configure>",
            lambda e: self.compare_canvas.configure(scrollregion=self.compare_canvas.bbox("all"))
        )

        self.compare_canvas.create_window((0, 0), window=self.compare_scrollable, anchor="nw")
        self.compare_canvas.configure(yscrollcommand=cmp_scrollbar_y.set, xscrollcommand=cmp_scrollbar_x.set)

        self.compare_canvas.grid(row=0, column=0, sticky="nsew")
        cmp_scrollbar_y.grid(row=0, column=1, sticky="ns")
        cmp_scrollbar_x.grid(row=1, column=0, sticky="ew")

        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.compare_scrollable.grid_columnconfigure(0, weight=1, minsize=500)
        self.compare_scrollable.grid_columnconfigure(1, weight=1, minsize=500)

        # 底部按钮
        bottom_frame = ttk.Frame(parent, padding="10")
        bottom_frame.pack(fill=tk.X)

        ttk.Button(bottom_frame, text="创建所有缺失项到目标",
                   command=self.create_all_missing).pack(side=tk.LEFT, padx=5)
        ttk.Button(bottom_frame, text="用源地址覆盖所有匹配项",
                   command=self.fill_all_from_source).pack(side=tk.LEFT, padx=5)
        ttk.Button(bottom_frame, text="保存目标文件",
                   command=self.save_target).pack(side=tk.RIGHT, padx=5)
        ttk.Button(bottom_frame, text="目标另存为...",
                   command=self.save_target_as).pack(side=tk.RIGHT)

    # ================================================================
    #  单文件模式 方法（原有功能）
    # ================================================================

    def browse_file(self):
        """浏览选择.graph文件"""
        file_path = filedialog.askopenfilename(
            title="选择.graph文件",
            filetypes=[("Graph files", "*.graph"), ("All files", "*.*")]
        )
        if file_path:
            self.file_path_var.set(file_path)
            self.file_path = file_path

    def parse_file(self):
        """解析.graph文件，提取所有特效地址"""
        if not self.file_path:
            messagebox.showwarning("警告", "请先选择.graph文件")
            return

        if not os.path.exists(self.file_path):
            messagebox.showerror("错误", "文件不存在")
            return

        try:
            self.effect_addresses = []
            self.address_entries = []

            for widget in self.scrollable_frame.winfo_children():
                widget.destroy()

            self.tree = ET.parse(self.file_path)
            root = self.tree.getroot()

            self.find_effect_addresses(root)

            if not self.effect_addresses:
                messagebox.showinfo("信息", "未找到特效地址")
                self.status_var.set("未找到特效地址")
                return

            self.initial_addresses = [addr_info['original'] for addr_info in self.effect_addresses]
            self.display_addresses()
            self.status_var.set(f"找到 {len(self.effect_addresses)} 个特效地址")

        except ET.ParseError as e:
            messagebox.showerror("错误", f"XML解析错误: {str(e)}")
        except Exception as e:
            messagebox.showerror("错误", f"解析文件时出错: {str(e)}")

    def find_effect_addresses(self, element, parent_map=None):
        """查找所有特效地址（Type为32765的Cue）"""
        if parent_map is None:
            parent_map = {}
            self._build_parent_map(element, parent_map)

        for cue in element.findall(".//Cue"):
            type_elem = cue.find("Type")
            if type_elem is not None and type_elem.text == "32765":
                data_elem = cue.find("Data")
                name_elem = cue.find("Name")
                track_name = cue.find("_TrackName")

                if data_elem is not None and data_elem.text:
                    node_info = track_name.text if track_name is not None else "Effect"
                    parent_name = self.get_parent_name(cue, parent_map)

                    self.effect_addresses.append({
                        'node': data_elem,
                        'original': data_elem.text,
                        'path': node_info,
                        'name': name_elem.text if name_elem is not None else "Effect",
                        'parent': parent_name
                    })

    def _build_parent_map(self, element, parent_map, parent=None):
        """递归构建父节点映射"""
        if parent is not None:
            parent_map[element] = parent
        for child in element:
            self._build_parent_map(child, parent_map, element)

    def get_parent_name(self, element, parent_map):
        """获取父节点的名称"""
        current = element
        while current in parent_map:
            current = parent_map[current]
            if current.tag == "Input":
                name_elem = current.find("Name")
                if name_elem is not None and name_elem.text:
                    return name_elem.text
        return "Unknown"

    def display_addresses(self):
        """在界面上显示所有地址，左右对齐"""
        for i, addr_info in enumerate(self.effect_addresses):
            # 左侧显示原始地址信息
            left_frame = ttk.Frame(self.scrollable_frame, relief=tk.GROOVE, borderwidth=1)
            left_frame.grid(row=i, column=0, sticky="nsew", padx=(0, 2), pady=1)

            left_content_frame = ttk.Frame(left_frame)
            left_content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            path_label = ttk.Label(
                left_content_frame,
                text=f"{i+1}. [{addr_info['path']}]",
                foreground="blue",
                font=("Arial", 9, "bold")
            )
            path_label.pack(anchor=tk.W, padx=5, pady=(3, 0))

            parent_label = ttk.Label(
                left_content_frame,
                text=f"节点: {addr_info['parent']}",
                foreground="gray",
                font=("Arial", 8)
            )
            parent_label.pack(anchor=tk.W, padx=5)

            addr_label = ttk.Label(
                left_content_frame,
                text=addr_info['original'],
                wraplength=450,
                justify=tk.LEFT
            )
            addr_label.pack(anchor=tk.W, padx=5, pady=(0, 3))

            def copy_to_clipboard(addr=addr_info['original']):
                self.root.clipboard_clear()
                self.root.clipboard_append(addr)
                self.status_var.set(f"已复制地址到剪切板: {addr[:50]}...")

            copy_btn = ttk.Button(
                left_frame,
                text="复制",
                width=6,
                command=copy_to_clipboard
            )
            copy_btn.pack(side=tk.RIGHT, padx=5, pady=5)

            # 右侧输入框
            right_frame = ttk.Frame(self.scrollable_frame, relief=tk.GROOVE, borderwidth=1)
            right_frame.grid(row=i, column=1, sticky="nsew", padx=(2, 0), pady=1)

            right_path_label = ttk.Label(
                right_frame,
                text=f"{i+1}. [{addr_info['path']}]",
                foreground="blue",
                font=("Arial", 9, "bold")
            )
            right_path_label.pack(anchor=tk.W, padx=5, pady=(3, 0))

            right_parent_label = ttk.Label(
                right_frame,
                text=f"节点: {addr_info['parent']}",
                foreground="gray",
                font=("Arial", 8)
            )
            right_parent_label.pack(anchor=tk.W, padx=5)

            entry_frame = ttk.Frame(right_frame)
            entry_frame.pack(fill=tk.X, padx=5, pady=(0, 3))

            entry_var = tk.StringVar(value=addr_info['original'])
            entry = ttk.Entry(
                entry_frame,
                textvariable=entry_var,
                width=55
            )
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

            def paste_from_clipboard(entry_var=entry_var):
                try:
                    clipboard_content = self.root.clipboard_get()
                    entry_var.set(clipboard_content)
                    self.status_var.set(f"已粘贴内容: {clipboard_content[:50]}...")
                except Exception:
                    self.status_var.set("剪切板为空或内容无效")

            paste_btn = ttk.Button(
                entry_frame,
                text="粘贴",
                width=6,
                command=paste_from_clipboard
            )
            paste_btn.pack(side=tk.RIGHT, padx=(5, 0))

            self.address_entries.append(entry_var)

    def replace_all_with_right(self):
        """将所有特效地址替换为右侧输入的新地址"""
        if not self.effect_addresses:
            messagebox.showwarning("警告", "请先解析文件")
            return

        result = messagebox.askyesno("确认", "确定要将所有特效地址替换为右侧输入的新地址吗？")
        if not result:
            return

        count = 0
        for i, addr_info in enumerate(self.effect_addresses):
            new_address = self.address_entries[i].get()
            addr_info['node'].text = new_address
            count += 1

        self.status_var.set(f"已替换 {count} 个特效地址为新地址")
        messagebox.showinfo("完成", f"已成功替换 {count} 个特效地址为新地址")

    def batch_replace_prefix(self):
        """批量替换前缀"""
        dialog = tk.Toplevel(self.root)
        dialog.title("批量替换前缀")
        dialog.geometry("400x150")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="原前缀:").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        old_prefix_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=old_prefix_var, width=30).grid(row=0, column=1, padx=10, pady=10)

        ttk.Label(dialog, text="新前缀:").grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        new_prefix_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=new_prefix_var, width=30).grid(row=1, column=1, padx=10, pady=10)

        def apply_replace():
            old_prefix = old_prefix_var.get()
            new_prefix = new_prefix_var.get()

            if not old_prefix:
                messagebox.showwarning("警告", "请输入原前缀")
                return

            count = 0
            for i, entry_var in enumerate(self.address_entries):
                current = entry_var.get()
                if current.startswith(old_prefix):
                    new_addr = new_prefix + current[len(old_prefix):]
                    entry_var.set(new_addr)
                    count += 1

            dialog.destroy()
            self.status_var.set(f"已替换 {count} 个地址的前缀")

        ttk.Button(dialog, text="应用", command=apply_replace).grid(row=2, column=0, columnspan=2, pady=20)

    def reset_to_initial(self):
        """将所有右侧输入框还原为初始地址"""
        if not self.effect_addresses:
            messagebox.showwarning("警告", "请先解析文件")
            return

        if not self.initial_addresses:
            messagebox.showwarning("警告", "没有初始地址数据")
            return

        result = messagebox.askyesno("确认", "确定要将所有地址还原为初始值吗？")
        if not result:
            return

        count = 0
        for i, entry_var in enumerate(self.address_entries):
            if i < len(self.initial_addresses):
                entry_var.set(self.initial_addresses[i])
                count += 1

        self.status_var.set(f"已还原 {count} 个地址为初始值")
        messagebox.showinfo("完成", f"已成功还原 {count} 个地址为初始值")

    def save_file(self):
        """保存修改到原文件"""
        if not self.file_path or not self.tree:
            messagebox.showwarning("警告", "请先解析文件")
            return
        self._save_to_file(self.file_path)

    def save_file_as(self):
        """另存为新文件"""
        if not self.tree:
            messagebox.showwarning("警告", "请先解析文件")
            return

        file_path = filedialog.asksaveasfilename(
            title="保存为",
            defaultextension=".graph",
            filetypes=[("Graph files", "*.graph"), ("All files", "*.*")]
        )
        if file_path:
            self._save_to_file(file_path)

    def _save_to_file(self, file_path):
        """执行保存操作"""
        try:
            for i, addr_info in enumerate(self.effect_addresses):
                new_address = self.address_entries[i].get()
                addr_info['node'].text = new_address

            self.tree.write(file_path, encoding='utf-8', xml_declaration=True)

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            content = self.format_xml(content)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            self.status_var.set(f"已保存到: {file_path}")
            messagebox.showinfo("成功", f"文件已保存到:\n{file_path}")

        except Exception as e:
            messagebox.showerror("错误", f"保存文件时出错: {str(e)}")

    # ================================================================
    #  对比模式 方法（新功能）
    # ================================================================

    def browse_source(self):
        """浏览选择源文件"""
        file_path = filedialog.askopenfilename(
            title="选择源文件(.graph)",
            filetypes=[("Graph files", "*.graph"), ("All files", "*.*")]
        )
        if file_path:
            self.source_path_var.set(file_path)

    def browse_target(self):
        """浏览选择目标文件"""
        file_path = filedialog.askopenfilename(
            title="选择目标文件(.graph)",
            filetypes=[("Graph files", "*.graph"), ("All files", "*.*")]
        )
        if file_path:
            self.target_path_var.set(file_path)

    def _build_full_parent_map(self, root):
        """构建完整的父节点映射（迭代方式）"""
        parent_map = {}
        for parent in root.iter():
            for child in parent:
                parent_map[child] = parent
        return parent_map

    def _get_structural_path(self, node, parent_map):
        """
        计算节点在XML树中的结构路径。
        返回元组，例如: (('Graph', 0), ('Inputs', 0), ('Input', 2), ('Cues', 0), ('Cue', 1))
        每一级是 (标签名, 在同标签兄弟中的索引)。
        """
        path = []
        current = node
        while current in parent_map:
            parent = parent_map[current]
            idx = 0
            for child in parent:
                if child is current:
                    break
                if child.tag == current.tag:
                    idx += 1
            path.insert(0, (current.tag, idx))
            current = parent
        return tuple(path)

    def _get_parent_input_name(self, element, parent_map):
        """获取父Input节点的名称"""
        current = element
        while current in parent_map:
            current = parent_map[current]
            if current.tag == "Input":
                name_elem = current.find("Name")
                if name_elem is not None and name_elem.text:
                    return name_elem.text
        return "Unknown"

    def _collect_cues_with_paths(self, root):
        """
        收集所有Type=32765的Cue节点，附带结构路径信息。
        返回列表: [{cue, data_node, address, struct_path, track_name, name, parent_name}, ...]
        """
        parent_map = self._build_full_parent_map(root)
        cues = []

        for cue in root.findall(".//Cue"):
            type_elem = cue.find("Type")
            if type_elem is not None and type_elem.text == "32765":
                data_elem = cue.find("Data")
                name_elem = cue.find("Name")
                track_name = cue.find("_TrackName")

                struct_path = self._get_structural_path(cue, parent_map)
                parent_name = self._get_parent_input_name(cue, parent_map)

                cues.append({
                    'cue': cue,
                    'data_node': data_elem,
                    'address': data_elem.text if data_elem is not None and data_elem.text else '',
                    'struct_path': struct_path,
                    'track_name': track_name.text if track_name is not None else 'Effect',
                    'name': name_elem.text if name_elem is not None else 'Effect',
                    'parent_name': parent_name,
                })

        return cues

    def parse_compare(self):
        """解析并对比两个graph文件"""
        source_path = self.source_path_var.get()
        target_path = self.target_path_var.get()

        if not source_path or not target_path:
            messagebox.showwarning("警告", "请选择源文件和目标文件")
            return

        if not os.path.exists(source_path):
            messagebox.showerror("错误", f"源文件不存在:\n{source_path}")
            return

        if not os.path.exists(target_path):
            messagebox.showerror("错误", f"目标文件不存在:\n{target_path}")
            return

        try:
            # 清空
            self.compare_results = []
            self.compare_entries = []
            self.compare_right_frames = []
            for widget in self.compare_scrollable.winfo_children():
                widget.destroy()

            # 解析源文件
            self.source_tree = ET.parse(source_path)
            source_root = self.source_tree.getroot()
            source_cues = self._collect_cues_with_paths(source_root)

            # 解析目标文件
            self.target_tree = ET.parse(target_path)
            target_root = self.target_tree.getroot()
            target_cues = self._collect_cues_with_paths(target_root)

            # 构建目标文件的结构路径索引
            target_by_path = {cue['struct_path']: cue for cue in target_cues}

            # 以源文件为基准逐个匹配
            matched_count = 0
            missing_count = 0
            diff_count = 0

            for src_cue in source_cues:
                tgt_cue = target_by_path.get(src_cue['struct_path'])

                if tgt_cue:
                    status = 'matched'
                    if src_cue['address'] != tgt_cue['address']:
                        status = 'diff'
                        diff_count += 1
                    matched_count += 1
                else:
                    tgt_cue = None
                    status = 'missing'
                    missing_count += 1

                self.compare_results.append({
                    'source': src_cue,
                    'target': tgt_cue,
                    'status': status,
                })

            if not self.compare_results:
                messagebox.showinfo("信息", "源文件中未找到Type=32765的特效节点")
                self.status_var.set("源文件中未找到特效节点")
                return

            # 显示结果
            self.display_compare_results()

            # 更新统计
            same_count = matched_count - diff_count
            stats = (f"源文件: {len(source_cues)} 个特效  |  "
                     f"目标文件: {len(target_cues)} 个特效  |  "
                     f"一致: {same_count}  |  "
                     f"地址不同: {diff_count}  |  "
                     f"目标缺失: {missing_count}")
            self.compare_stats_var.set(stats)
            self.status_var.set(f"对比完成：一致 {same_count}，不同 {diff_count}，缺失 {missing_count}")

        except ET.ParseError as e:
            messagebox.showerror("错误", f"XML解析错误: {str(e)}")
        except Exception as e:
            messagebox.showerror("错误", f"解析文件时出错: {str(e)}")

    def display_compare_results(self):
        """显示对比结果"""
        self.compare_entries = []
        self.compare_right_frames = []

        for i, result in enumerate(self.compare_results):
            src = result['source']
            tgt = result['target']
            status = result['status']

            # ---- 左侧：源文件信息 ----
            left_frame = ttk.Frame(self.compare_scrollable, relief=tk.GROOVE, borderwidth=1)
            left_frame.grid(row=i, column=0, sticky="nsew", padx=(0, 2), pady=1)

            left_content = ttk.Frame(left_frame)
            left_content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            ttk.Label(
                left_content,
                text=f"{i+1}. [{src['track_name']}]",
                foreground="blue",
                font=("Arial", 9, "bold")
            ).pack(anchor=tk.W, padx=5, pady=(3, 0))

            ttk.Label(
                left_content,
                text=f"节点: {src['parent_name']}",
                foreground="gray",
                font=("Arial", 8)
            ).pack(anchor=tk.W, padx=5)

            ttk.Label(
                left_content,
                text=src['address'] if src['address'] else '(空)',
                wraplength=450,
                justify=tk.LEFT
            ).pack(anchor=tk.W, padx=5, pady=(0, 3))

            # 源地址复制按钮
            def copy_src(addr=src['address']):
                self.root.clipboard_clear()
                self.root.clipboard_append(addr)
                self.status_var.set(f"已复制: {addr[:60]}...")

            ttk.Button(left_frame, text="复制", width=5, command=copy_src).pack(
                side=tk.RIGHT, padx=5, pady=5)

            # ---- 右侧：目标文件信息 ----
            right_frame = self._create_right_frame(i, src, tgt, status)
            self.compare_right_frames.append(right_frame)

    def _create_right_frame(self, i, src, tgt, status):
        """创建对比模式右侧的一行frame，返回frame引用"""
        if status == 'missing':
            # 缺失：红色背景
            right_frame = tk.Frame(self.compare_scrollable, relief=tk.GROOVE,
                                   borderwidth=1, bg="#f8d7da")
            right_frame.grid(row=i, column=1, sticky="nsew", padx=(2, 0), pady=1)

            tk.Label(
                right_frame,
                text=f"{i+1}. [缺失]",
                foreground="#721c24",
                font=("Arial", 9, "bold"),
                bg="#f8d7da"
            ).pack(anchor=tk.W, padx=5, pady=(3, 0))

            tk.Label(
                right_frame,
                text="目标文件中未找到对应的特效节点",
                foreground="#721c24",
                font=("Arial", 8),
                bg="#f8d7da"
            ).pack(anchor=tk.W, padx=5)

            btn_frame = tk.Frame(right_frame, bg="#f8d7da")
            btn_frame.pack(fill=tk.X, padx=5, pady=(0, 3))

            tk.Label(
                btn_frame,
                text=f"源地址: {src['address']}",
                foreground="#856404",
                font=("Arial", 8),
                bg="#f8d7da",
                wraplength=350,
                justify=tk.LEFT
            ).pack(side=tk.LEFT, anchor=tk.W)

            # "创建到目标"按钮
            def do_create(row=i):
                self._create_cue_in_target(row)

            tk.Button(
                btn_frame,
                text="创建到目标",
                command=do_create,
                bg="#dc3545",
                fg="white",
                relief=tk.RAISED,
                font=("Arial", 8, "bold")
            ).pack(side=tk.RIGHT, padx=(5, 0))

            self.compare_entries.append({
                'entry_var': None,
                'target_cue': None,
                'status': 'missing',
            })

        elif status == 'diff':
            # 地址不同：黄色背景
            right_frame = tk.Frame(self.compare_scrollable, relief=tk.GROOVE,
                                   borderwidth=1, bg="#fff3cd")
            right_frame.grid(row=i, column=1, sticky="nsew", padx=(2, 0), pady=1)

            tk.Label(
                right_frame,
                text=f"{i+1}. [{tgt['track_name']}] -- 地址不同",
                foreground="#856404",
                font=("Arial", 9, "bold"),
                bg="#fff3cd"
            ).pack(anchor=tk.W, padx=5, pady=(3, 0))

            tk.Label(
                right_frame,
                text=f"节点: {tgt['parent_name']}",
                foreground="gray",
                font=("Arial", 8),
                bg="#fff3cd"
            ).pack(anchor=tk.W, padx=5)

            entry_frame = tk.Frame(right_frame, bg="#fff3cd")
            entry_frame.pack(fill=tk.X, padx=5, pady=(0, 3))

            entry_var = tk.StringVar(value=tgt['address'])
            entry = ttk.Entry(entry_frame, textvariable=entry_var, width=50)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

            def use_source(ev=entry_var, addr=src['address']):
                ev.set(addr)
                self.status_var.set(f"已填入源地址: {addr[:60]}...")

            tk.Button(entry_frame, text="<-源", width=4, command=use_source,
                      bg="#fff3cd", relief=tk.RAISED).pack(side=tk.RIGHT, padx=(5, 0))

            self.compare_entries.append({
                'entry_var': entry_var,
                'target_cue': tgt,
                'status': 'diff',
            })

        else:
            # 一致：正常显示
            right_frame = ttk.Frame(self.compare_scrollable, relief=tk.GROOVE, borderwidth=1)
            right_frame.grid(row=i, column=1, sticky="nsew", padx=(2, 0), pady=1)

            ttk.Label(
                right_frame,
                text=f"{i+1}. [{tgt['track_name']}]",
                foreground="green",
                font=("Arial", 9, "bold")
            ).pack(anchor=tk.W, padx=5, pady=(3, 0))

            ttk.Label(
                right_frame,
                text=f"节点: {tgt['parent_name']}",
                foreground="gray",
                font=("Arial", 8)
            ).pack(anchor=tk.W, padx=5)

            entry_frame = ttk.Frame(right_frame)
            entry_frame.pack(fill=tk.X, padx=5, pady=(0, 3))

            entry_var = tk.StringVar(value=tgt['address'])
            entry = ttk.Entry(entry_frame, textvariable=entry_var, width=50)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

            def use_source(ev=entry_var, addr=src['address']):
                ev.set(addr)
                self.status_var.set(f"已填入源地址: {addr[:60]}...")

            ttk.Button(entry_frame, text="<-源", width=4, command=use_source).pack(
                side=tk.RIGHT, padx=(5, 0))

            self.compare_entries.append({
                'entry_var': entry_var,
                'target_cue': tgt,
                'status': 'matched',
            })

        return right_frame

    def _navigate_target_tree(self, target_root, path_steps):
        """
        沿着结构路径在目标树中导航。
        path_steps: 例如 (('Inputs', 0), ('Input', 2), ('Cues', 0))
        返回对应的节点，如果路径不存在则返回 None。
        """
        current = target_root
        for tag, idx in path_steps:
            count = 0
            found = None
            for child in current:
                if child.tag == tag:
                    if count == idx:
                        found = child
                        break
                    count += 1
            if found is None:
                return None
            current = found
        return current

    def _insert_cue_at_path(self, target_root, struct_path, source_cue_element):
        """
        将源Cue的深拷贝插入到目标树的对应位置。
        struct_path: 源Cue的完整结构路径，例如 (('Inputs',0), ('Input',2), ('Cues',0), ('Cue',1))
        返回新插入的Cue元素，失败返回None。
        """
        parent_path = struct_path[:-1]
        cue_tag, cue_idx = struct_path[-1]

        # 导航到父节点
        parent_node = self._navigate_target_tree(target_root, parent_path)
        if parent_node is None:
            return None

        # 深拷贝源Cue
        new_cue = copy.deepcopy(source_cue_element)

        # 计算插入位置：找到同tag子节点的位置列表
        cue_positions = []
        for j, child in enumerate(parent_node):
            if child.tag == cue_tag:
                cue_positions.append(j)

        if cue_idx < len(cue_positions):
            # 在第 cue_idx 个同tag子节点之前插入
            insert_pos = cue_positions[cue_idx]
        elif cue_positions:
            # 超出范围，追加到最后一个同tag子节点之后
            insert_pos = cue_positions[-1] + 1
        else:
            # 没有同tag子节点，追加到父节点末尾
            insert_pos = len(list(parent_node))

        parent_node.insert(insert_pos, new_cue)
        return new_cue

    def _create_cue_in_target(self, row_index):
        """将源文件的Cue节点创建到目标文件的同一位置，并就地更新UI"""
        result = self.compare_results[row_index]

        if result['status'] != 'missing':
            return

        src = result['source']
        target_root = self.target_tree.getroot()

        # 插入到目标树
        new_cue = self._insert_cue_at_path(target_root, src['struct_path'], src['cue'])
        if new_cue is None:
            messagebox.showerror("错误",
                f"无法在目标文件中找到对应的父节点位置。\n"
                f"结构路径: {src['struct_path']}\n"
                f"两个文件的上层结构可能不一致。")
            return

        # 构建新的目标Cue信息
        data_node = new_cue.find("Data")
        name_elem = new_cue.find("Name")
        track_name_elem = new_cue.find("_TrackName")
        parent_map = self._build_full_parent_map(target_root)
        parent_name = self._get_parent_input_name(new_cue, parent_map)

        tgt_info = {
            'cue': new_cue,
            'data_node': data_node,
            'address': data_node.text if data_node is not None and data_node.text else '',
            'struct_path': src['struct_path'],
            'track_name': track_name_elem.text if track_name_elem is not None else 'Effect',
            'name': name_elem.text if name_elem is not None else 'Effect',
            'parent_name': parent_name,
        }

        # 更新数据
        result['target'] = tgt_info
        result['status'] = 'matched'

        # 销毁旧的右侧frame
        old_frame = self.compare_right_frames[row_index]
        old_frame.destroy()

        # 重建为已匹配状态（绿色，带编辑框）
        # 需要先把 compare_entries[row_index] 临时移除，因为 _create_right_frame 会 append
        # 这里直接手动构建，避免 append 破坏索引
        right_frame = ttk.Frame(self.compare_scrollable, relief=tk.GROOVE, borderwidth=1)
        right_frame.grid(row=row_index, column=1, sticky="nsew", padx=(2, 0), pady=1)

        ttk.Label(
            right_frame,
            text=f"{row_index+1}. [{tgt_info['track_name']}] -- 已创建",
            foreground="#155724",
            font=("Arial", 9, "bold")
        ).pack(anchor=tk.W, padx=5, pady=(3, 0))

        ttk.Label(
            right_frame,
            text=f"节点: {tgt_info['parent_name']}",
            foreground="gray",
            font=("Arial", 8)
        ).pack(anchor=tk.W, padx=5)

        entry_frame = ttk.Frame(right_frame)
        entry_frame.pack(fill=tk.X, padx=5, pady=(0, 3))

        entry_var = tk.StringVar(value=tgt_info['address'])
        entry = ttk.Entry(entry_frame, textvariable=entry_var, width=50)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        def use_source(ev=entry_var, addr=src['address']):
            ev.set(addr)
            self.status_var.set(f"已填入源地址: {addr[:60]}...")

        ttk.Button(entry_frame, text="<-源", width=4, command=use_source).pack(
            side=tk.RIGHT, padx=(5, 0))

        # 更新引用
        self.compare_right_frames[row_index] = right_frame
        self.compare_entries[row_index] = {
            'entry_var': entry_var,
            'target_cue': tgt_info,
            'status': 'matched',
        }

        self.status_var.set(f"已创建第 {row_index+1} 项到目标文件")
        self._update_compare_stats()

    def create_all_missing(self):
        """将所有缺失项的Cue节点创建到目标文件"""
        if not self.compare_results:
            messagebox.showwarning("警告", "请先解析对比")
            return

        missing_indices = [i for i, r in enumerate(self.compare_results) if r['status'] == 'missing']
        if not missing_indices:
            messagebox.showinfo("信息", "没有缺失项需要创建")
            return

        confirm = messagebox.askyesno("确认",
            f"确定要将 {len(missing_indices)} 个缺失的Cue节点创建到目标文件吗？")
        if not confirm:
            return

        success = 0
        fail = 0
        for idx in missing_indices:
            result = self.compare_results[idx]
            if result['status'] != 'missing':
                continue
            src = result['source']
            target_root = self.target_tree.getroot()
            new_cue = self._insert_cue_at_path(target_root, src['struct_path'], src['cue'])
            if new_cue is None:
                fail += 1
                continue

            # 构建目标Cue信息
            data_node = new_cue.find("Data")
            name_elem = new_cue.find("Name")
            track_name_elem = new_cue.find("_TrackName")
            parent_map = self._build_full_parent_map(target_root)
            parent_name = self._get_parent_input_name(new_cue, parent_map)

            tgt_info = {
                'cue': new_cue,
                'data_node': data_node,
                'address': data_node.text if data_node is not None and data_node.text else '',
                'struct_path': src['struct_path'],
                'track_name': track_name_elem.text if track_name_elem is not None else 'Effect',
                'name': name_elem.text if name_elem is not None else 'Effect',
                'parent_name': parent_name,
            }

            result['target'] = tgt_info
            result['status'] = 'matched'

            # 更新UI
            old_frame = self.compare_right_frames[idx]
            old_frame.destroy()

            right_frame = ttk.Frame(self.compare_scrollable, relief=tk.GROOVE, borderwidth=1)
            right_frame.grid(row=idx, column=1, sticky="nsew", padx=(2, 0), pady=1)

            ttk.Label(
                right_frame,
                text=f"{idx+1}. [{tgt_info['track_name']}] -- 已创建",
                foreground="#155724",
                font=("Arial", 9, "bold")
            ).pack(anchor=tk.W, padx=5, pady=(3, 0))

            ttk.Label(
                right_frame,
                text=f"节点: {tgt_info['parent_name']}",
                foreground="gray",
                font=("Arial", 8)
            ).pack(anchor=tk.W, padx=5)

            entry_frame = ttk.Frame(right_frame)
            entry_frame.pack(fill=tk.X, padx=5, pady=(0, 3))

            entry_var = tk.StringVar(value=tgt_info['address'])
            entry = ttk.Entry(entry_frame, textvariable=entry_var, width=50)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

            def use_source(ev=entry_var, addr=src['address']):
                ev.set(addr)
                self.status_var.set(f"已填入源地址: {addr[:60]}...")

            ttk.Button(entry_frame, text="<-源", width=4, command=use_source).pack(
                side=tk.RIGHT, padx=(5, 0))

            self.compare_right_frames[idx] = right_frame
            self.compare_entries[idx] = {
                'entry_var': entry_var,
                'target_cue': tgt_info,
                'status': 'matched',
            }
            success += 1

        msg = f"成功创建 {success} 个缺失项到目标文件"
        if fail > 0:
            msg += f"，{fail} 个因父节点不存在而失败"
        self.status_var.set(msg)
        messagebox.showinfo("完成", msg)
        self._update_compare_stats()

    def _update_compare_stats(self):
        """更新对比统计信息"""
        if not self.compare_results:
            return
        matched = sum(1 for r in self.compare_results if r['status'] == 'matched')
        diff = sum(1 for r in self.compare_results if r['status'] == 'diff')
        missing = sum(1 for r in self.compare_results if r['status'] == 'missing')
        same = matched  # matched 不含 diff
        total_src = len(self.compare_results)
        stats = (f"源文件: {total_src} 个特效  |  "
                 f"一致/已创建: {same}  |  "
                 f"地址不同: {diff}  |  "
                 f"目标缺失: {missing}")
        self.compare_stats_var.set(stats)
        self.status_var.set(f"一致/已创建 {same}，不同 {diff}，缺失 {missing}")

    def fill_all_from_source(self):
        """用源地址覆盖所有匹配项的目标地址"""
        if not self.compare_results:
            messagebox.showwarning("警告", "请先解析对比")
            return

        result = messagebox.askyesno("确认", "确定要将所有匹配项的目标地址替换为源地址吗？")
        if not result:
            return

        count = 0
        for i, res in enumerate(self.compare_results):
            entry_info = self.compare_entries[i]
            if entry_info['entry_var'] is not None and res['source']:
                entry_info['entry_var'].set(res['source']['address'])
                count += 1

        self.status_var.set(f"已将 {count} 个匹配项的目标地址替换为源地址")

    def save_target(self):
        """保存目标文件"""
        if not self.target_tree:
            messagebox.showwarning("警告", "请先解析文件")
            return

        target_path = self.target_path_var.get()
        if not target_path:
            messagebox.showwarning("警告", "目标文件路径为空")
            return

        self._save_target_to(target_path)

    def save_target_as(self):
        """目标文件另存为"""
        if not self.target_tree:
            messagebox.showwarning("警告", "请先解析文件")
            return

        file_path = filedialog.asksaveasfilename(
            title="保存目标文件为",
            defaultextension=".graph",
            filetypes=[("Graph files", "*.graph"), ("All files", "*.*")]
        )
        if file_path:
            self._save_target_to(file_path)

    def _save_target_to(self, file_path):
        """保存目标文件到指定路径"""
        try:
            # 将编辑框中的值写回目标XML树
            for entry_info in self.compare_entries:
                if (entry_info['entry_var'] is not None
                        and entry_info['target_cue'] is not None
                        and entry_info['target_cue']['data_node'] is not None):
                    entry_info['target_cue']['data_node'].text = entry_info['entry_var'].get()

            self.target_tree.write(file_path, encoding='utf-8', xml_declaration=True)

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            content = self.format_xml(content)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            self.status_var.set(f"已保存到: {file_path}")
            messagebox.showinfo("成功", f"目标文件已保存到:\n{file_path}")

        except Exception as e:
            messagebox.showerror("错误", f"保存文件时出错: {str(e)}")

    # ================================================================
    #  共用方法
    # ================================================================

    def format_xml(self, content):
        """简单的XML格式化"""
        try:
            from xml.dom import minidom
            dom = minidom.parseString(content)
            pretty_xml = dom.toprettyxml(indent='\t', encoding='utf-8')
            lines = pretty_xml.decode('utf-8').split('\n')
            lines = [line for line in lines if line.strip()]
            return '\n'.join(lines)
        except Exception:
            return content


def main():
    root = tk.Tk()
    app = EffectAddressReplacer(root)
    root.mainloop()

if __name__ == "__main__":
    main()
