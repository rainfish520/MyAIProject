# -*- coding: utf-8 -*-
"""
Graph文件生成器 - 数据模型模块
用于存储和管理图结构的内部数据
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from enum import Enum
import uuid


class StructureType(Enum):
    """结构类型枚举"""
    THREE_STAGE = "三段式"      # start -> loop -> end
    INSTANT = "瞬发"            # 瞬发型


class CarType(Enum):
    """车辆类型枚举"""
    NEW_CAR = "新车"            # 新车
    OLD_CAR = "老车"            # 老车


class NodeType(Enum):
    """节点类型枚举"""
    STATE_MACHINE = "StateMachine"
    BLEND_TREE = "BlendTree"
    ACTION_NODE = "ActionNode"


@dataclass
class Event:
    """事件数据"""
    _TrackName: str = "Event01"
    TimePer: float = 0
    Name: str = ""
    
    def to_dict(self) -> Dict:
        return {"_TrackName": self._TrackName, "TimePer": self.TimePer, "Name": self.Name}


@dataclass
class Cue:
    """提示/特效数据"""
    _TrackName: str = ""
    TimePer: float = 0
    Name: str = ""
    Data: str = ""
    Type: int = 1
    Oneshot: bool = True
    
    def to_dict(self) -> Dict:
        return {
            "_TrackName": self._TrackName,
            "TimePer": self.TimePer,
            "Name": self.Name,
            "Data": self.Data,
            "Type": self.Type,
            "Oneshot": str(self.Oneshot).lower()
        }


@dataclass
class GraphNode:
    """图节点"""
    node_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    node_type: str = "ActionNode"  # StateMachine, BlendTree, ActionNode
    name: str = ""
    scene_pos_x: float = 0
    scene_pos_y: float = 0
    anim_name: str = "no_anim"
    add_ref_time: float = 0
    single_play: bool = True
    events: List[Event] = field(default_factory=list)
    cues: List[Cue] = field(default_factory=list)
    
    # StateMachine专用
    transitions: List[Dict] = field(default_factory=list)
    start_node: str = ""
    blend_tree_input: Optional['GraphNode'] = None
    state_machine_input: Optional['GraphNode'] = None
    
    # BlendTree专用
    result_pos_x: float = 220
    result_pos_y: float = 40
    
    def add_event(self, event: Event):
        self.events.append(event)
    
    def add_cue(self, cue: Cue):
        self.cues.append(cue)
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "Type": self.node_type,
            "Name": self.name,
            "_ScenePos": f"{self.scene_pos_x} {self.scene_pos_y}"
        }
        
        # 添加动画相关属性
        if self.node_type == "ActionNode":
            if self.events:
                for event in self.events:
                    result.update(event.to_dict())
            if self.cues:
                for cue in self.cues:
                    result.update(cue.to_dict())
            result["AnimName"] = self.anim_name
            result["AddRefTime"] = self.add_ref_time
            result["SinglePlay"] = str(self.single_play).lower()
        
        # BlendTree特有
        elif self.node_type == "BlendTree":
            result["Input"] = {}
            result["_ResultPos"] = f"{self.result_pos_x} {self.result_pos_y}"
        
        # StateMachine特有
        elif self.node_type == "StateMachine":
            result["_ScenePos"] = f"{self.scene_pos_x} {self.scene_pos_y}"
            
        return result


@dataclass
class Transition:
    """转换关系"""
    name: str = ""
    start: str = ""
    end: str = ""
    duration: float = 0
    event: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "Name": self.name,
            "Start": self.start,
            "End": self.end,
            "Duration": self.duration,
            "Event": self.event
        }


@dataclass
class GraphLayer:
    """图层/页签"""
    layer_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "NewLayer"
    structure_type: StructureType = StructureType.THREE_STAGE
    nodes: List[GraphNode] = field(default_factory=list)
    transitions: List[Transition] = field(default_factory=list)
    scene_pos_x: float = 275
    scene_pos_y: float = 32
    share_event: bool = True
    
    # 车辆类型（新车/老车）- 每个技能单独设置
    car_type: CarType = CarType.NEW_CAR
    
    # 场所和类型设置（每个技能单独设置）
    # 展厅车身/展厅底盘/赛道车身/赛道底盘 - 单选
    enable_showroom_body: bool = True    # 展厅车身
    enable_showroom_chassis: bool = False  # 展厅底盘
    enable_race_body: bool = True       # 赛道车身
    enable_race_chassis: bool = False     # 赛道底盘
    
    # 三段式专用
    start_node: Optional[GraphNode] = None
    loop_node: Optional[GraphNode] = None
    end_node: Optional[GraphNode] = None
    blend_tree: Optional[GraphNode] = None
    state_machine: Optional[GraphNode] = None
    
    # 瞬发式专用
    instant_blend_tree: Optional[GraphNode] = None
    instant_action_nodes: List[GraphNode] = field(default_factory=list)
    
    def create_three_stage_structure(self):
        """创建三段式结构"""
        self.structure_type = StructureType.THREE_STAGE
        self.nodes = []
        self.transitions = []
        
        # 创建BlendTree节点
        bt = GraphNode(
            node_type="BlendTree",
            name="BlendTree_#1",
            scene_pos_x=-192,
            scene_pos_y=-165,
            result_pos_x=220,
            result_pos_y=40
        )
        self.blend_tree = bt
        self.nodes.append(bt)
        
        # 创建StateMachine节点（包含start, loop, end）
        sm = GraphNode(
            node_type="StateMachine",
            name="StateMachine",
            scene_pos_x=-193,
            scene_pos_y=109
        )
        self.state_machine = sm
        self.nodes.append(sm)
        
        # 在StateMachine内创建三个ActionNode
        start_node = GraphNode(
            node_type="ActionNode",
            name="start",
            scene_pos_x=-425,
            scene_pos_y=75,
            events=[Event(_TrackName="Event01", TimePer=0, Name="start_end_01")]
        )
        
        loop_node = GraphNode(
            node_type="ActionNode",
            name="loop01",
            scene_pos_x=-100,
            scene_pos_y=-224,
            single_play=False  # loop节点默认循环播放
        )
        
        end_node = GraphNode(
            node_type="ActionNode",
            name="end",
            scene_pos_x=200,
            scene_pos_y=76,
            events=[Event(_TrackName="Event01", TimePer=1, Name="cus_end_01")]
        )
        
        # 添加到节点列表
        self.nodes.extend([start_node, loop_node, end_node])
        self.start_node = start_node
        self.loop_node = loop_node
        self.end_node = end_node
        
        # 创建StateMachine内的转换
        sm_transitions = [
            Transition(name="start_to_loop", start="start", end="loop01", duration=0, event="start_end_01"),
            Transition(name="loop_to_end", start="loop01", end="end", duration=0, event="BigSkill_Stop_01"),
            Transition(name="loop_to_start", start="loop01", end="start", duration=0, event="BigSkill_Stop_01"),
            Transition(name="end_to_start", start="end", end="start", duration=0, event="BigSkill_Stop_01"),
            Transition(name="start_to_end", start="start", end="end", duration=0, event="BigSkill_Start_01"),
        ]
        
        # Layer级别的转换
        self.transitions = [
            Transition(name="BlendTree_to_StateMachine", start="BlendTree_#1", end="StateMachine", 
                      duration=0, event="BigSkill_Start_01"),
            Transition(name="StateMachine_to_BlendTree_#1", start="StateMachine", end="BlendTree_#1", 
                      duration=0, event="cus_end_01"),
        ]
        
        # 保存内部转换到state_machine
        self.state_machine.transitions = [t.to_dict() for t in sm_transitions]
        self.state_machine.start_node = "start"
    
    def create_instant_structure(self):
        """创建瞬发式结构"""
        self.structure_type = StructureType.INSTANT
        self.nodes = []
        self.transitions = []
        
        # 创建BlendTree
        bt = GraphNode(
            node_type="BlendTree",
            name="BlendTree",
            scene_pos_x=350,
            scene_pos_y=-25,
            result_pos_x=220,
            result_pos_y=40
        )
        self.instant_blend_tree = bt
        self.nodes.append(bt)
        
        # 创建ActionNode (no_anim)
        no_anim1 = GraphNode(
            node_type="ActionNode",
            name="no_anim",
            scene_pos_x=350,
            scene_pos_y=177,
            events=[Event(_TrackName="Event01", TimePer=1, Name="add_power_stop_01")]
        )
        
        # 创建ActionNode (no_anim_#1)
        no_anim2 = GraphNode(
            node_type="ActionNode",
            name="no_anim_#1",
            scene_pos_x=853,
            scene_pos_y=180,
            events=[Event(_TrackName="Event01", TimePer=1, Name="add_power_stop_01")]
        )
        
        self.instant_action_nodes = [no_anim1, no_anim2]
        self.nodes.extend(self.instant_action_nodes)
        
        # 创建转换
        self.transitions = [
            Transition(name="BlendTree_to_no_anim", start="BlendTree", end="no_anim", 
                      duration=0, event="add_power_start_01"),
            Transition(name="no_anim_#1_to_no_anim", start="no_anim_#1", end="no_anim", 
                      duration=0, event="add_power_start_01"),
            Transition(name="no_anim_#1_to_BlendTree", start="no_anim_#1", end="BlendTree", 
                      duration=0, event="add_power_stop_01"),
            Transition(name="no_anim_to_BlendTree", start="no_anim", end="BlendTree", 
                      duration=0, event="add_power_stop_01"),
            Transition(name="no_anim_to_no_anim_#1", start="no_anim", end="no_anim_#1", 
                      duration=0, event="add_power_start_01"),
        ]
        
        # StateMachine节点
        sm = GraphNode(
            node_type="StateMachine",
            name="瞬发",
            scene_pos_x=-125,
            scene_pos_y=132,
            transitions=[t.to_dict() for t in self.transitions],
            start_node="BlendTree"
        )
        self.state_machine = sm
        self.nodes.append(sm)


@dataclass
class GraphModel:
    """完整的图模型"""
    graph_name: str = "graph"
    layers: List[GraphLayer] = field(default_factory=list)
    events: List[str] = field(default_factory=list)
    
    def add_layer(self, structure_type: StructureType = StructureType.THREE_STAGE) -> GraphLayer:
        """添加新图层"""
        layer = GraphLayer()
        layer.name = f"Layer{len(self.layers) + 1}"
        
        if structure_type == StructureType.THREE_STAGE:
            layer.create_three_stage_structure()
        else:
            layer.create_instant_structure()
        
        self.layers.append(layer)
        return layer
    
    def remove_layer(self, index: int):
        """删除图层"""
        if 0 <= index < len(self.layers):
            self.layers.pop(index)
    
    def get_default_events(self) -> List[str]:
        """获取默认事件列表"""
        return [
            "BigSkill_Start", "BigSkill_Start_01", "BigSkill_Stop", "BigSkill_Stop_01",
            "Effect", "Speed_Up_oneSelf", "Speed_Up_oneSelf_end",
            "add_power_A", "add_power_start", "add_power_start_01", "add_power_stop", "add_power_stop_01",
            "cus_end_01", "cus_end_02", "custom_end", "custom_end_B",
            "fallback_Start", "fallback_finish", "power_end_A",
            "start_end", "start_end_01", "start_end_02", "start_end_B", "start_end_C"
        ]
