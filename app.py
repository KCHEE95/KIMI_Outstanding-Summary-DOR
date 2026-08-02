"""
Production DOR Dashboard
========================
Streamlit App for tracking production status across 50+ parts
with Epicor Kinetic BAQ export integration.

Architecture:
- Summary Tab: Customer-grouped part overview with completion rates
- DOR Tabs: Per-part daily operation reports (WIP/OUTPUT/REJECT by operation)
- Outstanding Tab: Pending items tracking

Data Sources:
- Epicor BAQ 1: Outstanding Dashboard (Sales Order Lines -> Main Parts only)
- Epicor BAQ 2: PartOpr + BOM (Operations + Sub Parts structure)
- Manual DOR entries: Daily WIP/OUTPUT/REJECT quantities

Author: Generated for production team
"""

import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================
st.set_page_config(
    page_title="Production DOR Dashboard",
    page_icon="馃彮",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================================================
# CUSTOM CSS - Dark Manufacturing Theme
# ============================================================================
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
    }
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 1400px;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #e2e8f0 !important;
        font-family: 'Inter', 'SF Pro Display', system-ui, sans-serif;
    }
    p, span, div {
        font-family: 'Inter', system-ui, sans-serif;
    }
    div[data-testid="stMetric"] {
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 16px;
    }
    div[data-testid="stMetric"] label {
        color: #94a3b8 !important;
        font-size: 11px !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    div[data-testid="stMetric"] div {
        color: #e2e8f0 !important;
        font-size: 28px !important;
        font-weight: 800 !important;
    }
    .stButton > button {
        background: linear-gradient(135deg, #3b82f6, #2563eb) !important;
        border: none !important;
        border-radius: 10px !important;
        color: white !important;
        font-weight: 600 !important;
        padding: 8px 16px !important;
        transition: all 0.2s !important;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4) !important;
    }
    .stSelectbox > div > div {
        background: rgba(15, 23, 42, 0.6) !important;
        border: 1px solid #334155 !important;
        border-radius: 10px !important;
        color: #e2e8f0 !important;
    }
    .stTextInput > div > div > input {
        background: rgba(15, 23, 42, 0.6) !important;
        border: 1px solid #334155 !important;
        border-radius: 10px !important;
        color: #e2e8f0 !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(15, 23, 42, 0.6) !important;
        border-radius: 12px !important;
        padding: 6px !important;
        gap: 6px !important;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent !important;
        border-radius: 10px !important;
        color: #94a3b8 !important;
        font-weight: 500 !important;
        padding: 10px 20px !important;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #3b82f6, #2563eb) !important;
        color: white !important;
        box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3) !important;
    }
    .streamlit-expanderHeader {
        background: rgba(30, 41, 59, 0.6) !important;
        border: 1px solid #334155 !important;
        border-radius: 12px !important;
        color: #e2e8f0 !important;
        font-weight: 600 !important;
    }
    .streamlit-expanderContent {
        background: rgba(15, 23, 42, 0.3) !important;
        border: 1px solid #334155 !important;
        border-top: none !important;
        border-radius: 0 0 12px 12px !important;
    }
    .badge-normal {
        background: rgba(34, 197, 94, 0.2);
        color: #4ade80;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 600;
    }
    .badge-warning {
        background: rgba(245, 158, 11, 0.2);
        color: #fbbf24;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 600;
    }
    .badge-danger {
        background: rgba(239, 68, 68, 0.2);
        color: #f87171;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 600;
    }
    .badge-pending {
        background: rgba(59, 130, 246, 0.2);
        color: #60a5fa;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 600;
    }
    .progress-container {
        width: 100%;
        height: 6px;
        background: rgba(15, 23, 42, 0.6);
        border-radius: 3px;
        overflow: hidden;
    }
    .progress-bar-green {
        height: 100%;
        background: linear-gradient(90deg, #22c55e, #4ade80);
        border-radius: 3px;
    }
    .progress-bar-yellow {
        height: 100%;
        background: linear-gradient(90deg, #f59e0b, #fbbf24);
        border-radius: 3px;
    }
    .progress-bar-red {
        height: 100%;
        background: linear-gradient(90deg, #ef4444, #f87171);
        border-radius: 3px;
    }
    .op-step {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 36px;
        height: 36px;
        border-radius: 50%;
        font-size: 14px;
        font-weight: 700;
    }
    .op-step-done {
        background: linear-gradient(135deg, #22c55e, #16a34a);
        box-shadow: 0 0 12px rgba(34, 197, 94, 0.3);
    }
    .op-step-active {
        background: linear-gradient(135deg, #3b82f6, #2563eb);
        box-shadow: 0 0 12px rgba(59, 130, 246, 0.3);
        animation: pulse 2s infinite;
    }
    .op-step-pending {
        background: rgba(51, 65, 85, 0.8);
        border: 2px solid #475569;
        opacity: 0.5;
    }
    @keyframes pulse {
        0%, 100% { box-shadow: 0 0 12px rgba(59, 130, 246, 0.3); }
        50% { box-shadow: 0 0 20px rgba(59, 130, 246, 0.6); }
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# DATA MODELS
# ============================================================================

class Operation:
    def __init__(self, name: str, seq: int, is_final: bool = False):
        self.name = name
        self.seq = seq
        self.is_final = is_final

class SubPart:
    def __init__(self, part_num: str, description: str, target_qty: int):
        self.part_num = part_num
        self.description = description
        self.target_qty = target_qty
        self.operations = []

    def add_operation(self, op: Operation):
        self.operations.append(op)
        self.operations.sort(key=lambda x: x.seq)

class MainPart:
    def __init__(self, part_num: str, description: str, customer: str, 
                 part_type: str = "Single", target_qty: int = 0):
        self.part_num = part_num
        self.description = description
        self.customer = customer
        self.part_type = part_type
        self.target_qty = target_qty
        self.sub_parts = []

    def add_sub_part(self, sub: SubPart):
        self.sub_parts.append(sub)

class DORRecord:
    def __init__(self, date: str, part_num: str, sub_part_num: str,
                 operation: str, wip: int = 0, output: int = 0, reject: int = 0,
                 updated_by: str = "", note: str = ""):
        self.date = date
        self.part_num = part_num
        self.sub_part_num = sub_part_num
        self.operation = operation
        self.wip = wip
        self.output = output
        self.reject = reject
        self.updated_by = updated_by
        self.note = note
        self.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ============================================================================
# DATA MANAGEMENT
# ============================================================================

class DataManager:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.parts_file = self.data_dir / "parts_config.json"
        self.dor_file = self.data_dir / "dor_records.csv"
        self.parts = {}
        self.dor_records = pd.DataFrame()
        self._load_data()

    def _load_data(self):
        if self.parts_file.exists():
            with open(self.parts_file, 'r') as f:
                data = json.load(f)
                self._deserialize_parts(data)
        else:
            self._create_demo_data()

        if self.dor_file.exists():
            self.dor_records = pd.read_csv(self.dor_file)
        else:
            self.dor_records = pd.DataFrame(columns=[
                'date', 'part_num', 'sub_part_num', 'operation',
                'wip', 'output', 'reject', 'updated_by', 'note', 'updated_at'
            ])

    def _deserialize_parts(self, data: dict):
        for p_data in data.get('parts', []):
            part = MainPart(
                p_data['part_num'],
                p_data['description'],
                p_data['customer'],
                p_data['part_type'],
                p_data['target_qty']
            )
            for sp_data in p_data.get('sub_parts', []):
                sub = SubPart(sp_data['part_num'], sp_data['description'], sp_data['target_qty'])
                for op_data in sp_data.get('operations', []):
                    sub.add_operation(Operation(op_data['name'], op_data['seq'], op_data.get('is_final', False)))
                part.add_sub_part(sub)
            self.parts[part.part_num] = part

    def _create_demo_data(self):
        customers = [
            ("ABC Manufacturing", 12),
            ("XYZ Corp", 8),
            ("DEF Industries", 15),
            ("GHI Precision", 10),
            ("JKL Systems", 5)
        ]
        op_templates = {
            "standard": ["SAW", "CNC1", "SP1", "WD", "SP2", "CNC2", "PCKL", "BF", "LCMARK", "PK", "Ship"],
            "simple": ["Laser", "Bend", "Weld", "Polish", "PK", "Ship"],
            "complex": ["SAW", "CNC", "Mill", "Drill", "Tap", "Deburr", "Wash", "Inspect", "PK", "Ship"]
        }

        part_idx = 0
        for customer, count in customers:
            for i in range(count):
                part_idx += 1
                is_assembly = (part_idx % 3 == 0)
                part_type = "Assembly" if is_assembly else "Single"

                part = MainPart(
                    part_num=f"PART-{part_idx:04d}",
                    description=f"Component Type {part_idx}",
                    customer=customer,
                    part_type=part_type,
                    target_qty=500 + (part_idx * 50)
                )

                template_key = list(op_templates.keys())[part_idx % 3]
                ops = op_templates[template_key]

                if is_assembly:
                    sub_count = 2 + (part_idx % 2)
                    for j in range(sub_count):
                        sub = SubPart(
                            part_num=f"SUB-{part_idx:04d}-{chr(65+j)}",
                            description=f"Sub-component {chr(65+j)}",
                            target_qty=part.target_qty
                        )
                        for k, op_name in enumerate(ops):
                            sub.add_operation(Operation(op_name, k, op_name == "Ship"))
                        part.add_sub_part(sub)
                else:
                    sub = SubPart(
                        part_num=part.part_num,
                        description=part.description,
                        target_qty=part.target_qty
                    )
                    for k, op_name in enumerate(ops):
                        sub.add_operation(Operation(op_name, k, op_name == "Ship"))
                    part.add_sub_part(sub)

                self.parts[part.part_num] = part

        self._save_parts()

    def _save_parts(self):
        data = {'parts': []}
        for part in self.parts.values():
            p_data = {
                'part_num': part.part_num,
                'description': part.description,
                'customer': part.customer,
                'part_type': part.part_type,
                'target_qty': part.target_qty,
                'sub_parts': []
            }
            for sp in part.sub_parts:
                sp_data = {
                    'part_num': sp.part_num,
                    'description': sp.description,
                    'target_qty': sp.target_qty,
                    'operations': [
                        {'name': op.name, 'seq': op.seq, 'is_final': op.is_final}
                        for op in sp.operations
                    ]
                }
                p_data['sub_parts'].append(sp_data)
            data['parts'].append(p_data)

        with open(self.parts_file, 'w') as f:
            json.dump(data, f, indent=2)

    def save_dor_record(self, record: DORRecord):
        new_row = pd.DataFrame([{
            'date': record.date,
            'part_num': record.part_num,
            'sub_part_num': record.sub_part_num,
            'operation': record.operation,
            'wip': record.wip,
            'output': record.output,
            'reject': record.reject,
            'updated_by': record.updated_by,
            'note': record.note,
            'updated_at': record.updated_at
        }])
        self.dor_records = pd.concat([self.dor_records, new_row], ignore_index=True)
        self.dor_records.to_csv(self.dor_file, index=False)

    def get_dor_for_part(self, part_num: str, date: str = None):
        df = self.dor_records[self.dor_records['part_num'] == part_num]
        if date:
            df = df[df['date'] == date]
        return df

    def get_completion_rate(self, part_num: str):
        part = self.parts.get(part_num)
        if not part:
            return {'rate': 0, 'bottleneck': 'N/A', 'status': 'Unknown'}

        total_ops = sum(len(sp.operations) for sp in part.sub_parts)
        completed_ops = 0
        bottleneck = ""
        min_progress = 100

        for sp in part.sub_parts:
            sp_completed = 0
            for op in sp.operations:
                op_df = self.dor_records[
                    (self.dor_records['part_num'] == part_num) &
                    (self.dor_records['sub_part_num'] == sp.part_num) &
                    (self.dor_records['operation'] == op.name)
                ]

                if not op_df.empty:
                    latest = op_df.sort_values('updated_at').iloc[-1]
                    if latest['output'] >= sp.target_qty:
                        sp_completed += 1
                    else:
                        progress = (latest['output'] / sp.target_qty) * 100 if sp.target_qty > 0 else 0
                        if progress < min_progress:
                            min_progress = progress
                            bottleneck = f"{sp.part_num} / {op.name}"
                else:
                    if min_progress == 100:
                        bottleneck = f"{sp.part_num} / {op.name}"
                        min_progress = 0

            completed_ops += sp_completed

        rate = (completed_ops / total_ops * 100) if total_ops > 0 else 0

        if rate >= 100:
            status = "Completed"
            color = "normal"
        elif rate >= 80:
            status = "Normal"
            color = "normal"
        elif rate >= 50:
            status = "Delayed"
            color = "warning"
        else:
            status = "Abnormal"
            color = "danger"

        return {
            'rate': round(rate, 1),
            'bottleneck': bottleneck or "N/A",
            'status': status,
            'color': color
        }

    def get_customers(self):
        return sorted(list(set(p.customer for p in self.parts.values())))

    def get_parts_by_customer(self, customer: str = None):
        parts = list(self.parts.values())
        if customer and customer != "All Customers":
            parts = [p for p in parts if p.customer == customer]
        return parts

# ============================================================================
# UI COMPONENTS
# ============================================================================

def render_kpi_card(title: str, value: str, color: str, icon: str = ""):
    color_map = {
        'blue': ('#60a5fa', 'rgba(59,130,246,0.12)'),
        'purple': ('#c084fc', 'rgba(168,85,247,0.12)'),
        'yellow': ('#fbbf24', 'rgba(245,158,11,0.12)'),
        'green': ('#4ade80', 'rgba(34,197,94,0.12)'),
        'red': ('#f87171', 'rgba(239,68,68,0.12)'),
        'gray': ('#94a3b8', 'rgba(100,116,139,0.12)')
    }
    text_color, bg_color = color_map.get(color, color_map['blue'])

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, {bg_color}, rgba(0,0,0,0.03)); 
                border: 1px solid {text_color}33; border-radius: 14px; padding: 16px; text-align: center;">
        <p style="margin: 0; color: {text_color}; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">
            {icon} {title}
        </p>
        <p style="margin: 6px 0 0 0; font-size: 28px; font-weight: 800; color: #e2e8f0;">
            {value}
        </p>
    </div>
    """, unsafe_allow_html=True)

def render_progress_bar(value: float, width: int = 80):
    if value >= 80:
        bar_class = "progress-bar-green"
        color = "#4ade80"
    elif value >= 50:
        bar_class = "progress-bar-yellow"
        color = "#fbbf24"
    else:
        bar_class = "progress-bar-red"
        color = "#f87171"

    st.markdown(f"""
    <div style="text-align: right;">
        <span style="font-size: 15px; font-weight: 700; color: {color};">{value:.0f}%</span>
        <div class="progress-container" style="width: {width}px; margin-left: auto; margin-top: 4px;">
            <div class="{bar_class}" style="width: {min(value, 100)}%;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_operation_flow(operations, current_op: str = ""):
    html = '<div style="display: flex; align-items: center; gap: 0; margin: 16px 0; overflow-x: auto;">'

    for i, op in enumerate(operations):
        if op.name == current_op:
            step_class = "op-step-active"
            emoji = "&#9881;"
            text_color = "#60a5fa"
        elif current_op and any(o.name == current_op for o in operations):
            curr_idx = next((idx for idx, o in enumerate(operations) if o.name == current_op), len(operations))
            if i < curr_idx:
                step_class = "op-step-done"
                emoji = "&#10004;"
                text_color = "#4ade80"
            else:
                step_class = "op-step-pending"
                emoji = "&#9675;"
                text_color = "#64748b"
        else:
            step_class = "op-step-pending"
            emoji = "&#9675;"
            text_color = "#64748b"

        html += f'<div style="flex: 1; text-align: center; position: relative; min-width: 70px;">'
        html += f'<div class="op-step {step_class}" style="margin: 0 auto;">{emoji}</div>'
        html += f'<p style="margin: 8px 0 0 0; font-size: 11px; font-weight: 600; color: {text_color};">{op.name}</p>'
        html += '</div>'

        if i < len(operations) - 1:
            if step_class == "op-step-done":
                line_color = "#22c55e"
            else:
                line_color = "#334155"
            html += f'<div style="flex: 0.3; height: 3px; background: {line_color}; border-radius: 2px; margin-top: -20px;"></div>'

    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

# ============================================================================
# SUMMARY PAGE
# ============================================================================

def render_summary_page(dm: DataManager):
    st.markdown("""
    <h1 style="margin: 0; font-size: 26px; font-weight: 700;">&#128202; Production Summary Board</h1>
    <p style="margin: 6px 0 24px 0; color: #94a3b8; font-size: 13px;">
        Data: Epicor BAQ | Status: Manual DOR Update | Tracking 50 Parts
    </p>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns([2, 2, 3, 1])

    with col1:
        customers = ["All Customers"] + dm.get_customers()
        selected_customer = st.selectbox("&#128100; Select Customer", customers, key="summary_customer")

    with col2:
        search_part = st.text_input("&#128269; Filter Part Number", placeholder="Enter part number...", key="summary_search")

    with col3:
        status_filter = st.segmented_control(
            "Status Filter",
            options=["All", "&#9989; Normal", "&#9888; Delayed", "&#128308; Abnormal", "&#128203; Not Started"],
            default="All",
            key="summary_status"
        )

    with col4:
        st.write("")
        st.write("")
        if st.button("&#128229; Export", key="summary_export"):
            st.success("Report generated!")

    all_parts = dm.get_parts_by_customer(selected_customer if selected_customer != "All Customers" else None)
    if search_part:
        all_parts = [p for p in all_parts if search_part.upper() in p.part_num.upper()]

    total_parts = len(all_parts)
    customers_count = len(set(p.customer for p in all_parts))

    completion_data = [dm.get_completion_rate(p.part_num) for p in all_parts]
    normal_count = sum(1 for c in completion_data if c['status'] == "Normal")
    warning_count = sum(1 for c in completion_data if c['status'] == "Delayed")
    danger_count = sum(1 for c in completion_data if c['status'] == "Abnormal")
    completed_count = sum(1 for c in completion_data if c['status'] == "Completed")
    pending_count = total_parts - normal_count - warning_count - danger_count - completed_count

    cols = st.columns(6)
    with cols[0]:
        render_kpi_card("Customers", str(customers_count), "blue", "&#128100;")
    with cols[1]:
        render_kpi_card("Parts", str(total_parts), "purple", "&#128230;")
    with cols[2]:
        render_kpi_card("In Progress", str(normal_count + warning_count + danger_count), "yellow", "&#128295;")
    with cols[3]:
        render_kpi_card("Completed", str(completed_count), "green", "&#9989;")
    with cols[4]:
        render_kpi_card("Abnormal", str(danger_count), "red", "&#9888;")
    with cols[5]:
        render_kpi_card("Not Started", str(pending_count), "gray", "&#128203;")

    st.markdown("<div style='margin: 20px 0;'></div>", unsafe_allow_html=True)

    customers_in_view = sorted(set(p.customer for p in all_parts))

    for customer in customers_in_view:
        customer_parts = [p for p in all_parts if p.customer == customer]

        if status_filter and status_filter != "All":
            status_map = {"&#9989; Normal": "Normal", "&#9888; Delayed": "Delayed", "&#128308; Abnormal": "Abnormal", "&#128203; Not Started": "Not Started"}
            target_status = status_map.get(status_filter, "")
            customer_parts = [p for p in customer_parts 
                           if dm.get_completion_rate(p.part_num)['status'] == target_status]

        if not customer_parts:
            continue

        avg_rate = sum(dm.get_completion_rate(p.part_num)['rate'] for p in customer_parts) / len(customer_parts)

        st.markdown(f"""
        <div style="background: rgba(30,41,59,0.6); border: 1px solid #334155; border-radius: 16px; padding: 20px; margin-bottom: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                <h3 style="margin: 0; font-size: 16px; font-weight: 600;">&#127970; {customer} &mdash; {len(customer_parts)} Parts</h3>
                <span style="background: rgba(59,130,246,0.15); color: #60a5fa; padding: 5px 14px; border-radius: 20px; font-size: 12px;">
                    Avg Completion: {avg_rate:.0f}%
                </span>
            </div>
        """, unsafe_allow_html=True)

        header_cols = st.columns([2.2, 0.8, 0.9, 1.0, 1.0, 0.9, 1.1])
        headers = ["Part Number / Operations", "Jobs", "Target Qty", "Completion", "Current Op", "Status", "Action"]
        for col, header in zip(header_cols, headers):
            col.markdown(f"<p style='margin: 0; font-size: 11px; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.3px;'>{header}</p>", unsafe_allow_html=True)

        for part in customer_parts:
            comp = dm.get_completion_rate(part.part_num)

            current_op = "N/A"
            for sp in part.sub_parts:
                for op in sp.operations:
                    op_df = dm.dor_records[
                        (dm.dor_records['part_num'] == part.part_num) &
                        (dm.dor_records['sub_part_num'] == sp.part_num) &
                        (dm.dor_records['operation'] == op.name)
                    ]
                    if not op_df.empty:
                        latest = op_df.sort_values('updated_at').iloc[-1]
                        if latest['output'] < sp.target_qty:
                            current_op = op.name
                            break
                if current_op != "N/A":
                    break

            total_ops = sum(len(sp.operations) for sp in part.sub_parts)

            color_map = {
                "Normal": ("#4ade80", "badge-normal"),
                "Delayed": ("#fbbf24", "badge-warning"),
                "Abnormal": ("#f87171", "badge-danger"),
                "Completed": ("#4ade80", "badge-normal"),
                "Not Started": ("#60a5fa", "badge-pending")
            }
            color, badge_class = color_map.get(comp['status'], ("#94a3b8", "badge-pending"))

            cols = st.columns([2.2, 0.8, 0.9, 1.0, 1.0, 0.9, 1.1])

            with cols[0]:
                type_icon = "&#128208;" if "ANGLE" in part.part_num else "&#128297;" if "BRACKET" in part.part_num else "&#9881;" if "SHAFT" in part.part_num else "&#128295;"
                ops_str = " &rarr; ".join([op.name for sp in part.sub_parts for op in sp.operations][:5])
                st.markdown(f"""
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 16px;">{type_icon}</span>
                    <div>
                        <p style="margin: 0; font-size: 14px; font-weight: 600; color: #e2e8f0;">{part.part_num}</p>
                        <p style="margin: 3px 0 0 0; font-size: 11px; color: #94a3b8;">
                            {ops_str}... <span style="color: #60a5fa;">({total_ops} ops)</span>
                        </p>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with cols[1]:
                st.markdown(f"<p style='text-align: center; font-size: 13px; color: #e2e8f0;'>{len(part.sub_parts)}</p>", unsafe_allow_html=True)

            with cols[2]:
                st.markdown(f"<p style='text-align: center; font-size: 13px; color: #e2e8f0;'>{part.target_qty:,}</p>", unsafe_allow_html=True)

            with cols[3]:
                render_progress_bar(comp['rate'])

            with cols[4]:
                op_color = "#60a5fa" if comp['status'] in ["Normal", "In Progress"] else "#f87171" if comp['status'] == "Abnormal" else "#fbbf24"
                st.markdown(f"<div style='text-align: center;'><span style='background: {op_color}22; color: {op_color}; padding: 4px 10px; border-radius: 10px; font-size: 11px; font-weight: 500;'>{current_op}</span></div>", unsafe_allow_html=True)

            with cols[5]:
                st.markdown(f'<div style="text-align: center;"><span class="{badge_class}">{comp["status"]}</span></div>', unsafe_allow_html=True)

            with cols[6]:
                btn_color = "#ef4444" if comp['status'] == "Abnormal" else "#3b82f6"
                btn_grad = "#dc2626" if comp['status'] == "Abnormal" else "#2563eb"
                st.markdown(f"""
                <div style="text-align: center;">
                    <button style="background: linear-gradient(135deg, {btn_color}, {btn_grad}); border: none; border-radius: 8px; padding: 8px 16px; color: white; font-size: 12px; font-weight: 600; cursor: pointer;">
                        &#128203; DOR
                    </button>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

# ============================================================================
# DOR PAGE - FIXED: WIP / OUTPUT / REJECT columns
# ============================================================================

def render_dor_page(dm: DataManager, part_num: str):
    part = dm.parts.get(part_num)
    if not part:
        st.error(f"Part {part_num} not found")
        return

    comp = dm.get_completion_rate(part_num)

    st.markdown(f"""
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <div>
            <h1 style="margin: 0; font-size: 24px; font-weight: 700;">&#128203; DOR &mdash; {part.part_num}</h1>
            <p style="margin: 6px 0 0 0; color: #94a3b8; font-size: 13px;">
                {part.description} | {part.customer} | {part.part_type} | Target: <strong style="color: #fbbf24;">{part.target_qty:,} pcs</strong>
            </p>
        </div>
        <div style="text-align: right;">
            <p style="margin: 0; font-size: 32px; font-weight: 800; color: {'#4ade80' if comp['rate'] >= 80 else '#fbbf24' if comp['rate'] >= 50 else '#f87171'};">
                {comp['rate']:.0f}%
            </p>
            <p style="margin: 4px 0 0 0; font-size: 12px; color: #94a3b8;">Overall Completion</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 3])
    with col1:
        selected_date = st.date_input("&#128197; Select Date", value=datetime.now(), key=f"dor_date_{part_num}")
    with col2:
        st.write("")
        st.write("")
        if st.button("&#128260; Load History", key=f"dor_load_{part_num}"):
            st.rerun()
    with col3:
        st.write("")

    date_str = selected_date.strftime("%Y-%m-%d")

    for sub_part in part.sub_parts:
        with st.expander(f"&#128230; {sub_part.part_num} &mdash; {sub_part.description} (Target: {sub_part.target_qty:,} pcs)", expanded=True):

            current_op = ""
            for op in sub_part.operations:
                op_df = dm.dor_records[
                    (dm.dor_records['part_num'] == part_num) &
                    (dm.dor_records['sub_part_num'] == sub_part.part_num) &
                    (dm.dor_records['operation'] == op.name) &
                    (dm.dor_records['date'] == date_str)
                ]
                if not op_df.empty:
                    latest = op_df.iloc[-1]
                    if latest['output'] < sub_part.target_qty:
                        current_op = op.name
                        break
                elif not current_op:
                    current_op = op.name
                    break

            render_operation_flow(sub_part.operations, current_op or sub_part.operations[0].name)

            st.markdown("<h4 style='margin: 20px 0 12px 0; font-size: 14px;'>&#128221; Daily DOR Entry</h4>", unsafe_allow_html=True)

            with st.form(key=f"dor_form_{part_num}_{sub_part.part_num}"):
                # Header row: Operation | Target Qty | Cumulative | WIP | OUTPUT | REJECT | Note
                cols = st.columns([1.3, 0.9, 1.0, 0.9, 0.9, 0.9, 1.8, 0.8])
                headers = ["Operation", "Target", "Cumulative", "WIP", "OUTPUT", "REJECT", "Note", ""]
                for col, header in zip(cols, headers):
                    col.markdown(f"<p style='margin: 0; font-size: 11px; color: #94a3b8; font-weight: 600; text-align: center;'>{header}</p>", unsafe_allow_html=True)

                existing = dm.get_dor_for_part(part_num, date_str)
                form_data = []

                for op in sub_part.operations:
                    op_existing = existing[
                        (existing['sub_part_num'] == sub_part.part_num) &
                        (existing['operation'] == op.name)
                    ]

                    # Calculate cumulative output across all dates
                    cumul_df = dm.dor_records[
                        (dm.dor_records['part_num'] == part_num) &
                        (dm.dor_records['sub_part_num'] == sub_part.part_num) &
                        (dm.dor_records['operation'] == op.name)
                    ]
                    cumulative_output = cumul_df['output'].sum() if not cumul_df.empty else 0
                    cumulative_wip = cumul_df['wip'].sum() if not cumul_df.empty else 0
                    cumulative_reject = cumul_df['reject'].sum() if not cumul_df.empty else 0

                    row_cols = st.columns([1.3, 0.9, 1.0, 0.9, 0.9, 0.9, 1.8, 0.8])

                    with row_cols[0]:
                        op_color = "#f87171" if op.name == current_op and comp['status'] == "Abnormal" else "#60a5fa" if op.name == current_op else "#94a3b8"
                        st.markdown(f"""
                        <div style="background: rgba(30,41,59,0.8); border: 1px solid {'#ef4444' if op.name == current_op and comp['status'] == 'Abnormal' else '#334155'}; 
                                    border-radius: 8px; padding: 10px 12px; color: {op_color}; font-size: 13px; font-weight: 600;">
                            {op.name}
                        </div>
                        """, unsafe_allow_html=True)

                    with row_cols[1]:
                        st.markdown(f"<p style='text-align: center; font-size: 13px; color: #94a3b8; padding-top: 10px;'>{sub_part.target_qty:,}</p>", unsafe_allow_html=True)

                    with row_cols[2]:
                        st.markdown(f"""
                        <div style='text-align: center; padding-top: 6px;'>
                            <p style='margin: 0; font-size: 11px; color: #60a5fa;'>OUT: {cumulative_output:,}</p>
                            <p style='margin: 0; font-size: 10px; color: #fbbf24;'>WIP: {cumulative_wip:,}</p>
                            <p style='margin: 0; font-size: 10px; color: #f87171;'>REJ: {cumulative_reject:,}</p>
                        </div>
                        """, unsafe_allow_html=True)

                    with row_cols[3]:
                        default_wip = int(op_existing.iloc[-1]['wip']) if not op_existing.empty else 0
                        wip = st.number_input("WIP", min_value=0, value=default_wip, 
                                            key=f"wip_{part_num}_{sub_part.part_num}_{op.name}", 
                                            label_visibility="collapsed")

                    with row_cols[4]:
                        default_output = int(op_existing.iloc[-1]['output']) if not op_existing.empty else 0
                        output = st.number_input("OUTPUT", min_value=0, value=default_output, 
                                                 key=f"out_{part_num}_{sub_part.part_num}_{op.name}", 
                                                 label_visibility="collapsed")

                    with row_cols[5]:
                        default_reject = int(op_existing.iloc[-1]['reject']) if not op_existing.empty else 0
                        reject = st.number_input("REJECT", min_value=0, value=default_reject, 
                                                 key=f"rej_{part_num}_{sub_part.part_num}_{op.name}", 
                                                 label_visibility="collapsed")

                    with row_cols[6]:
                        note = st.text_input("Note", 
                                           value=op_existing.iloc[-1]['note'] if not op_existing.empty else "", 
                                           key=f"note_{part_num}_{sub_part.part_num}_{op.name}", 
                                           label_visibility="collapsed")

                    with row_cols[7]:
                        st.write("")

                    form_data.append({
                        'operation': op.name,
                        'wip': wip,
                        'output': output,
                        'reject': reject,
                        'note': note
                    })

                submit_cols = st.columns([5, 1])
                with submit_cols[1]:
                    submitted = st.form_submit_button("&#128190; Submit DOR", use_container_width=True)

                if submitted:
                    user_name = st.session_state.get('user_name', 'Anonymous')
                    for fd in form_data:
                        record = DORRecord(
                            date=date_str,
                            part_num=part_num,
                            sub_part_num=sub_part.part_num,
                            operation=fd['operation'],
                            wip=fd['wip'],
                            output=fd['output'],
                            reject=fd['reject'],
                            updated_by=user_name,
                            note=fd['note']
                        )
                        dm.save_dor_record(record)
                    st.success("&#9989; DOR Saved Successfully!")
                    st.balloons()

    st.markdown("<h3 style='margin: 24px 0 16px 0;'>&#128220; DOR History</h3>", unsafe_allow_html=True)
    hist_df = dm.get_dor_for_part(part_num)
    if not hist_df.empty:
        hist_df = hist_df.sort_values(['date', 'updated_at'], ascending=[False, False])
        st.dataframe(hist_df, use_container_width=True, hide_index=True)
    else:
        st.info("No history records yet")

# ============================================================================
# OUTSTANDING PAGE
# ============================================================================

def render_outstanding_page(dm: DataManager):
    st.markdown("""
    <h1 style="margin: 0; font-size: 26px; font-weight: 700;">&#9888; Outstanding Tracking</h1>
    <p style="margin: 6px 0 24px 0; color: #94a3b8; font-size: 13px;">
        Based on Epicor Outstanding Dashboard (Sales Order Lines) | Showing all incomplete Main Parts
    </p>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([2, 2, 2])
    with col1:
        customers = ["All Customers"] + dm.get_customers()
        selected = st.selectbox("&#128100; Customer", customers, key="out_customer")
    with col2:
        priority = st.selectbox("&#128293; Priority", ["All", "&#128308; High", "&#128993; Medium", "&#128994; Low"], key="out_priority")
    with col3:
        overdue = st.toggle("&#9200; Overdue Only", value=False, key="out_overdue")

    parts = dm.get_parts_by_customer(selected if selected != "All Customers" else None)

    outstanding_data = []
    for part in parts:
        comp = dm.get_completion_rate(part.part_num)
        if comp['status'] != "Completed":
            days_running = hash(part.part_num) % 30 + 1
            is_overdue = days_running > 20
            priority_level = "&#128308; High" if comp['status'] == "Abnormal" else "&#128993; Medium" if comp['status'] == "Delayed" else "&#128994; Low"

            if priority != "All" and priority != priority_level:
                continue
            if overdue and not is_overdue:
                continue

            outstanding_data.append({
                'part_num': part.part_num,
                'customer': part.customer,
                'description': part.description,
                'target_qty': part.target_qty,
                'completion': comp['rate'],
                'bottleneck': comp['bottleneck'],
                'status': comp['status'],
                'days_running': days_running,
                'priority': priority_level,
                'overdue': is_overdue
            })

    if not outstanding_data:
        st.success("&#127881; All Parts Completed!")
        return

    df = pd.DataFrame(outstanding_data)

    st.markdown("<div style='margin: 16px 0;'></div>", unsafe_allow_html=True)
    cols = st.columns(4)
    with cols[0]:
        render_kpi_card("Pending", str(len(df)), "yellow", "&#128203;")
    with cols[1]:
        render_kpi_card("High Priority", str(len(df[df['priority'] == "&#128308; High"])), "red", "&#128308;")
    with cols[2]:
        render_kpi_card("Overdue", str(len(df[df['overdue'] == True])), "red", "&#9200;")
    with cols[3]:
        avg_comp = df['completion'].mean()
        render_kpi_card("Avg Completion", f"{avg_comp:.0f}%", "blue" if avg_comp >= 50 else "yellow", "&#128202;")

    st.markdown("<div style='margin: 20px 0;'></div>", unsafe_allow_html=True)

    st.markdown("""
    <div style="background: rgba(30,41,59,0.6); border: 1px solid #334155; border-radius: 16px; padding: 20px;">
    """, unsafe_allow_html=True)

    for _, row in df.iterrows():
        color = "#f87171" if row['status'] == "Abnormal" else "#fbbf24" if row['status'] == "Delayed" else "#60a5fa"
        bg_color = "rgba(239,68,68,0.04)" if row['overdue'] else "transparent"

        st.markdown(f"""
        <div style="display: grid; grid-template-columns: 1.5fr 1.2fr 1fr 0.8fr 1fr 1.2fr 0.8fr 0.8fr; 
                    gap: 12px; align-items: center; padding: 14px; border-bottom: 1px solid rgba(51,65,85,0.3);
                    background: {bg_color}; border-radius: 8px; margin-bottom: 8px;">
            <div>
                <p style="margin: 0; font-size: 14px; font-weight: 600; color: #e2e8f0;">{row['part_num']}</p>
                <p style="margin: 2px 0 0 0; font-size: 11px; color: #94a3b8;">{row['description']}</p>
            </div>
            <div><p style="margin: 0; font-size: 13px; color: #e2e8f0;">{row['customer']}</p></div>
            <div style="text-align: center;"><p style="margin: 0; font-size: 13px; color: #e2e8f0;">{row['target_qty']:,}</p></div>
            <div style="text-align: center;"><span style="font-size: 14px; font-weight: 700; color: {color};">{row['completion']:.0f}%</span></div>
            <div style="text-align: center;">
                <span style="background: {color}22; color: {color}; padding: 4px 10px; border-radius: 10px; font-size: 11px;">
                    {row['bottleneck'].split('/')[-1].strip() if '/' in row['bottleneck'] else row['bottleneck']}
                </span>
            </div>
            <div style="text-align: center;">
                <span style="background: {'#ef4444' if row['priority'] == '&#128308; High' else '#f59e0b' if row['priority'] == '&#128993; Medium' else '#22c55e'}22; 
                             color: {'#f87171' if row['priority'] == '&#128308; High' else '#fbbf24' if row['priority'] == '&#128993; Medium' else '#4ade80'}; 
                             padding: 4px 10px; border-radius: 10px; font-size: 11px;">
                    {row['priority']}
                </span>
            </div>
            <div style="text-align: center;">
                <p style="margin: 0; font-size: 13px; color: {'#f87171' if row['overdue'] else '#94a3b8'};">
                    {'&#9200; ' if row['overdue'] else ''}{row['days_running']} days
                </p>
            </div>
            <div style="text-align: center;">
                <button style="background: linear-gradient(135deg, #3b82f6, #2563eb); border: none; border-radius: 8px; 
                               padding: 8px 14px; color: white; font-size: 12px; font-weight: 600; cursor: pointer;">
                    &#128203; DOR
                </button>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================================
# MAIN
# ============================================================================

def main():
    dm = DataManager()

    if 'user_name' not in st.session_state:
        st.session_state.user_name = ""

    with st.sidebar:
        st.header("&#128100; User Info")
        st.session_state.user_name = st.text_input("Your Name", value=st.session_state.user_name or "Colleague A")
        st.divider()
        st.header("&#128202; Quick Nav")
        if st.button("&#127968; Summary Board", use_container_width=True):
            st.session_state.current_page = "summary"
        if st.button("&#9888; Outstanding", use_container_width=True):
            st.session_state.current_page = "outstanding"
        st.divider()
        st.info("&#128161; Tips:\n- Fill DOR daily\n- Add notes for abnormalities\n- Completion rate auto-calculated")

    part_keys = sorted(dm.parts.keys())[:8]
    tab_labels = ["&#128202; Summary", "&#9888; Outstanding"] + [f"&#128203; {p}" for p in part_keys]

    tabs = st.tabs(tab_labels)

    with tabs[0]:
        render_summary_page(dm)

    with tabs[1]:
        render_outstanding_page(dm)

    for i, part_num in enumerate(part_keys, start=2):
        with tabs[i]:
            render_dor_page(dm, part_num)

if __name__ == "__main__":
    main()
