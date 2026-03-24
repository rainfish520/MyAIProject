# -*- coding: utf-8 -*-
"""
Graph文件序列化器 - 完全匹配Generator_temp.graph结构
修复：Layer应该用Type=Layer，直接包含多个技能StateMachine
"""

import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from models import GraphModel, GraphLayer, GraphNode, Transition, StructureType


class GraphSerializer:
    """图文件序列化器"""
    
    def __init__(self, model: GraphModel):
        self.model = model
        # 分别统计三段式和瞬发式的数量，用于事件序列
        self.three_stage_count = sum(1 for l in model.layers if l.structure_type == StructureType.THREE_STAGE)
        self.instant_count = sum(1 for l in model.layers if l.structure_type == StructureType.INSTANT)
        # 当前处理到的序号
        self.three_stage_idx = 0
        self.instant_idx = 0
    
    def serialize(self) -> str:
        """序列化为.graph文件字符串"""
        # 创建根节点
        root = ET.Element("Root")
        
        # Input节点
        input_node = ET.SubElement(root, "Input")
        
        # Graph类型
        graph_type = ET.SubElement(input_node, "Type")
        graph_type.text = "Graph"
        
        graph_name = ET.SubElement(input_node, "Name")
        graph_name.text = self.model.graph_name
        
        # 内部Input - StateMachine
        inner_input = ET.SubElement(input_node, "Input")
        state_machine_type = ET.SubElement(inner_input, "Type")
        state_machine_type.text = "StateMachine"
        
        sm_name = ET.SubElement(inner_input, "Name")
        sm_name.text = "StateMachine"
        
        # BlendTree (生成模版)
        blend_tree = ET.SubElement(inner_input, "Input")
        bt_type = ET.SubElement(blend_tree, "Type")
        bt_type.text = "BlendTree"
        
        bt_name = ET.SubElement(blend_tree, "Name")
        bt_name.text = "生成模版"
        
        # Layer节点 - 重要：Type是Layer，直接包含所有技能
        layer_elem = ET.SubElement(blend_tree, "Input")
        layer_type = ET.SubElement(layer_elem, "Type")
        layer_type.text = "Layer"  # 这里是Layer，不是StateMachine
        
        layer_name = ET.SubElement(layer_elem, "Name")
        layer_name.text = "Layer"
        
        # 添加每个技能（作为Layer的直接子节点）
        for layer in self.model.layers:
            # 根据技能类型分别编号
            if layer.structure_type == StructureType.THREE_STAGE:
                self.three_stage_idx += 1
                skill_idx = self.three_stage_idx
            else:
                self.instant_idx += 1
                skill_idx = self.instant_idx
            
            self._add_skill_to_layer(layer_elem, layer, skill_idx)
        
        # 补齐空的Input (原始文件有5个空Input)
        total_inputs = len(self.model.layers)
        for _ in range(5):
            empty_input = ET.SubElement(layer_elem, "Input")
        
        # Layer的位置和设置
        layer_scene_pos = ET.SubElement(layer_elem, "_ScenePos")
        layer_scene_pos.text = "275 32"
        
        share_event = ET.SubElement(layer_elem, "ShareEvent")
        share_event.text = "true"
        
        # BlendTree位置
        scene_pos = ET.SubElement(inner_input, "_ScenePos")
        scene_pos.text = "-99 -50"
        
        result_pos = ET.SubElement(inner_input, "_ResultPos")
        result_pos.text = "575 157"
        
        # 开始节点
        start_node = ET.SubElement(inner_input, "StartNode")
        start_node.text = "生成模版"
        
        # 事件列表 - 需要根据技能生成
        self._add_events(input_node)
        
        # 配置
        config = ET.SubElement(input_node, "Config")
        mask_effect = ET.SubElement(config, "MaskEffect")
        mask_effect.text = "false"
        mask_sound = ET.SubElement(config, "MaskSound")
        mask_sound.text = "false"
        
        # 骨架文件
        skeleton = ET.SubElement(input_node, "_skeletonFile")
        skeleton.text = ""
        
        # 格式化输出
        return self._pretty_print(root)
    
    def _add_events(self, input_node: ET.Element):
        """添加事件列表"""
        # 基础事件
        base_events = [
            "BigSkill_Start", "BigSkill_Stop", "Effect",
            "Speed_Up_oneSelf", "Speed_Up_oneSelf_end",
            "add_power_A", "add_power_start", "add_power_stop",
            "custom_end", "fallback_Start", "fallback_finish", "power_end_A",
            "start_end"
        ]
        
        # 添加基础事件
        for event_name in base_events:
            event_elem = ET.SubElement(input_node, "Event")
            evt_name = ET.SubElement(event_elem, "Name")
            evt_name.text = event_name
        
        # 分别添加三段式和瞬发式的事件，按各自类型编号
        # 三段式事件
        for i in range(1, self.three_stage_count + 1):
            events = [
                f"BigSkill_Start_{i:02d}",
                f"BigSkill_Stop_{i:02d}",
                f"start_end_{i:02d}",
                f"cus_end_{i:02d}"
            ]
            for event_name in events:
                event_elem = ET.SubElement(input_node, "Event")
                evt_name = ET.SubElement(event_elem, "Name")
                evt_name.text = event_name
        
        # 瞬发式事件
        for i in range(1, self.instant_count + 1):
            events = [
                f"add_power_start_{i:02d}",
                f"add_power_stop_{i:02d}"
            ]
            for event_name in events:
                event_elem = ET.SubElement(input_node, "Event")
                evt_name = ET.SubElement(event_elem, "Name")
                evt_name.text = event_name
            
            for event_name in events:
                event_elem = ET.SubElement(input_node, "Event")
                evt_name = ET.SubElement(event_elem, "Name")
                evt_name.text = event_name
    
    def _add_skill_to_layer(self, layer_node: ET.Element, layer: GraphLayer, skill_index: int):
        """添加技能到Layer节点 - 直接作为Layer的子节点"""
        idx = skill_index  # skill_index已经是正确的编号，不需要+1
        
        # 直接创建技能的StateMachine（作为Layer的直接子节点）
        skill_sm = ET.SubElement(layer_node, "Input")
        
        skill_type = ET.SubElement(skill_sm, "Type")
        skill_type.text = "StateMachine"
        
        skill_name = ET.SubElement(skill_sm, "Name")
        # 使用技能的自定义名称
        skill_name.text = layer.name
        
        if layer.structure_type == StructureType.THREE_STAGE:
            self._add_three_stage_skill(skill_sm, layer, idx)
        else:
            self._add_instant_skill(skill_sm, layer, idx)
    
    def _add_three_stage_skill(self, skill_sm: ET.Element, layer: GraphLayer, idx: int):
        """添加三段式技能结构"""
        # 1. BlendTree_#1
        bt_elem = ET.SubElement(skill_sm, "Input")
        bt_type = ET.SubElement(bt_elem, "Type")
        bt_type.text = "BlendTree"
        bt_name = ET.SubElement(bt_elem, "Name")
        bt_name.text = "BlendTree_#1"
        bt_input = ET.SubElement(bt_elem, "Input")
        bt_scene_pos = ET.SubElement(bt_elem, "_ScenePos")
        bt_scene_pos.text = "-192 -165"
        bt_result_pos = ET.SubElement(bt_elem, "_ResultPos")
        bt_result_pos.text = "220 40"
        
        # 2. 内部的StateMachine (包含start, loop01, end)
        inner_sm = ET.SubElement(skill_sm, "Input")
        inner_sm_type = ET.SubElement(inner_sm, "Type")
        inner_sm_type.text = "StateMachine"
        
        inner_sm_name = ET.SubElement(inner_sm, "Name")
        inner_sm_name.text = "StateMachine"
        
        # start节点
        start_node = ET.SubElement(inner_sm, "Input")
        self._add_action_node(start_node, "start", -425, 75, 
                            [("Event01", 0, f"start_end_{idx:02d}")],
                            "no_anim", 0, True)
        
        # loop01节点 (包含特效和音效)
        loop_node = ET.SubElement(inner_sm, "Input")
        cues = [
            ("Effect01", 0, "Effect", "effect/car/ma/fx_ma_skill:body_scale_2:-1:01001100", 32765),
            ("Audio02", 0, "挂接音效事件", f"Sounds/;skill_zdhm.bnk;Play_sfx_skill_zdhm_intro;0;0;0;0;0", 1),
            ("Audio01", 0.02, "挂接音效事件", f"Sounds/;skill_zdhm.bnk;Play_sfx_skill_zdhm_loop;1;0;0.2;0;0", 1)
        ]
        # 从模型中读取loop节点的single_play值
        loop_single_play = layer.loop_node.single_play if layer.loop_node else False
        self._add_action_node_with_cues(loop_node, "loop01", -100, -224, [], 
                                        "no_anim", 0, loop_single_play, cues)
        
        # end节点
        end_node = ET.SubElement(inner_sm, "Input")
        self._add_action_node(end_node, "end", 200, 76,
                            [("Event01", 1, f"cus_end_{idx:02d}")],
                            "no_anim", 0, True)
        
        # 内部StateMachine的位置
        inner_sm_scene = ET.SubElement(inner_sm, "_ScenePos")
        inner_sm_scene.text = "-193 109"
        
        # 内部转换
        transitions = [
            ("start_to_loop", "start", "loop01", f"start_end_{idx:02d}"),
            ("loop_to_end", "loop01", "end", f"BigSkill_Stop_{idx:02d}"),
            ("loop_to_start", "loop01", "start", f"BigSkill_Stop_{idx:02d}"),
            ("end_to_start", "end", "start", f"BigSkill_Stop_{idx:02d}"),
            ("start_to_end", "start", "end", f"BigSkill_Start_{idx:02d}")
        ]
        
        for t_name, t_start, t_end, t_event in transitions:
            trans = ET.SubElement(inner_sm, "Transition")
            t_name_elem = ET.SubElement(trans, "Name")
            t_name_elem.text = t_name
            t_start_elem = ET.SubElement(trans, "Start")
            t_start_elem.text = t_start
            t_end_elem = ET.SubElement(trans, "End")
            t_end_elem.text = t_end
            t_dur = ET.SubElement(trans, "Duration")
            t_dur.text = "0"
            t_evt = ET.SubElement(trans, "Event")
            t_evt.text = t_event
        
        # 开始节点
        start_node_elem = ET.SubElement(inner_sm, "StartNode")
        start_node_elem.text = "start"
        
        # Layer级别的位置（技能在Layer中的位置）
        skill_scene = ET.SubElement(skill_sm, "_ScenePos")
        skill_scene.text = "-125 -18"
        
        # Layer级别的转换（BlendTree和StateMachine之间的转换）
        layer_trans = [
            ("BlendTree_#1_to_StateMachine", "BlendTree_#1", "StateMachine", f"BigSkill_Start_{idx:02d}"),
            ("StateMachine_to_BlendTree_#1", "StateMachine", "BlendTree_#1", f"cus_end_{idx:02d}")
        ]
        
        for t_name, t_start, t_end, t_event in layer_trans:
            trans = ET.SubElement(skill_sm, "Transition")
            t_name_elem = ET.SubElement(trans, "Name")
            t_name_elem.text = t_name
            t_start_elem = ET.SubElement(trans, "Start")
            t_start_elem.text = t_start
            t_end_elem = ET.SubElement(trans, "End")
            t_end_elem.text = t_end
            t_dur = ET.SubElement(trans, "Duration")
            t_dur.text = "0"
            t_evt = ET.SubElement(trans, "Event")
            t_evt.text = t_event
        
        # 开始节点
        skill_start = ET.SubElement(skill_sm, "StartNode")
        skill_start.text = "BlendTree_#1"
    
    def _add_instant_skill(self, skill_sm: ET.Element, layer: GraphLayer, idx: int):
        """添加瞬发式技能结构"""
        # 1. no_anim节点
        no_anim1 = ET.SubElement(skill_sm, "Input")
        self._add_action_node(no_anim1, "no_anim", 350, 177,
                            [("Event01", 1, f"add_power_stop_{idx:02d}")],
                            "no_anim", 0, True)
        
        # 2. no_anim_#1节点
        no_anim2 = ET.SubElement(skill_sm, "Input")
        self._add_action_node(no_anim2, "no_anim_#1", 853, 180,
                            [("Event01", 1, f"add_power_stop_{idx:02d}")],
                            "no_anim", 0, True)
        
        # 3. BlendTree节点
        bt_elem = ET.SubElement(skill_sm, "Input")
        bt_type = ET.SubElement(bt_elem, "Type")
        bt_type.text = "BlendTree"
        bt_name = ET.SubElement(bt_elem, "Name")
        bt_name.text = "BlendTree"
        bt_input = ET.SubElement(bt_elem, "Input")
        bt_scene = ET.SubElement(bt_elem, "_ScenePos")
        bt_scene.text = "350 -25"
        bt_result = ET.SubElement(bt_elem, "_ResultPos")
        bt_result.text = "220 40"
        
        # 位置
        skill_scene = ET.SubElement(skill_sm, "_ScenePos")
        skill_scene.text = "-125 132"
        
        # 转换
        transitions = [
            ("BlendTree_to_no_anim", "BlendTree", "no_anim", f"add_power_start_{idx:02d}"),
            ("no_anim_#1_to_no_anim", "no_anim_#1", "no_anim", f"add_power_start_{idx:02d}"),
            ("no_anim_#1_to_BlendTree", "no_anim_#1", "BlendTree", f"add_power_stop_{idx:02d}"),
            ("no_anim_to_BlendTree", "no_anim", "BlendTree", f"add_power_stop_{idx:02d}"),
            ("no_anim_to_no_anim_#1", "no_anim", "no_anim_#1", f"add_power_start_{idx:02d}")
        ]
        
        for t_name, t_start, t_end, t_event in transitions:
            trans = ET.SubElement(skill_sm, "Transition")
            t_name_elem = ET.SubElement(trans, "Name")
            t_name_elem.text = t_name
            t_start_elem = ET.SubElement(trans, "Start")
            t_start_elem.text = t_start
            t_end_elem = ET.SubElement(trans, "End")
            t_end_elem.text = t_end
            t_dur = ET.SubElement(trans, "Duration")
            t_dur.text = "0"
            t_evt = ET.SubElement(trans, "Event")
            t_evt.text = t_event
        
        # 开始节点
        start_node = ET.SubElement(skill_sm, "StartNode")
        start_node.text = "BlendTree"
    
    def _add_action_node(self, parent: ET.Element, name: str, pos_x: float, pos_y: float,
                        events: List[tuple], anim_name: str, add_ref: float, single_play: bool):
        """添加ActionNode"""
        node_type = ET.SubElement(parent, "Type")
        node_type.text = "ActionNode"
        
        node_name = ET.SubElement(parent, "Name")
        node_name.text = name
        
        scene_pos = ET.SubElement(parent, "_ScenePos")
        scene_pos.text = f"{pos_x} {pos_y}"
        
        # 添加事件
        for track_name, time_per, event_name in events:
            event_elem = ET.SubElement(parent, "Event")
            track = ET.SubElement(event_elem, "_TrackName")
            track.text = track_name
            time = ET.SubElement(event_elem, "TimePer")
            time.text = str(time_per)
            evt_name = ET.SubElement(event_elem, "Name")
            evt_name.text = event_name
        
        # 动画属性
        anim = ET.SubElement(parent, "AnimName")
        anim.text = anim_name
        
        add_ref_elem = ET.SubElement(parent, "AddRefTime")
        add_ref_elem.text = str(add_ref)
        
        single = ET.SubElement(parent, "SinglePlay")
        single.text = str(single_play).lower()
    
    def _add_action_node_with_cues(self, parent: ET.Element, name: str, pos_x: float, pos_y: float,
                                   events: List[tuple], anim_name: str, add_ref: float, 
                                   single_play: bool, cues: List[tuple]):
        """添加带特效的ActionNode"""
        node_type = ET.SubElement(parent, "Type")
        node_type.text = "ActionNode"
        
        node_name = ET.SubElement(parent, "Name")
        node_name.text = name
        
        scene_pos = ET.SubElement(parent, "_ScenePos")
        scene_pos.text = f"{pos_x} {pos_y}"
        
        # 添加事件
        for track_name, time_per, event_name in events:
            event_elem = ET.SubElement(parent, "Event")
            track = ET.SubElement(event_elem, "_TrackName")
            track.text = track_name
            time = ET.SubElement(event_elem, "TimePer")
            time.text = str(time_per)
            evt_name = ET.SubElement(event_elem, "Name")
            evt_name.text = event_name
        
        # 添加特效/音效
        for track_name, time_per, cue_name, cue_data, cue_type in cues:
            cue_elem = ET.SubElement(parent, "Cue")
            track = ET.SubElement(cue_elem, "_TrackName")
            track.text = track_name
            time = ET.SubElement(cue_elem, "TimePer")
            time.text = str(time_per)
            c_name = ET.SubElement(cue_elem, "Name")
            c_name.text = cue_name
            c_data = ET.SubElement(cue_elem, "Data")
            c_data.text = cue_data
            c_type = ET.SubElement(cue_elem, "Type")
            c_type.text = str(cue_type)
            oneshot = ET.SubElement(cue_elem, "Oneshot")
            oneshot.text = "true"
        
        # 动画属性
        anim = ET.SubElement(parent, "AnimName")
        anim.text = anim_name
        
        add_ref_elem = ET.SubElement(parent, "AddRefTime")
        add_ref_elem.text = str(add_ref)
        
        single = ET.SubElement(parent, "SinglePlay")
        single.text = str(single_play).lower()
    
    def _pretty_print(self, elem):
        """格式化XML输出"""
        import xml.dom.minidom
        rough_string = ET.tostring(elem, encoding='unicode')
        dom = xml.dom.minidom.parseString(rough_string)
        return dom.toprettyxml(indent="  ")
    
    def save_to_file(self, file_path: str):
        """保存到文件"""
        content = self.serialize()
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
