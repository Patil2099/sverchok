# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import bpy
from bpy.props import BoolProperty, EnumProperty
from sverchok.node_tree import SverchCustomTreeNode
from sverchok.data_structure import updateNode, match_long_repeat,throttle_and_update_node
from sverchok.utils.listutils import lists_flat
from sverchok.utils.nodes_mixins.recursive_nodes import SvRecursiveNode
from sverchok.utils.modules.polygon_utils import faces_modes_dict, pols_origin_modes_dict, tangent_modes_dict

from sverchok.utils.modules.edge_utils import edges_modes_dict
from sverchok.utils.modules.vertex_utils import vertex_modes_dict


modes_dicts = {
    'Verts': vertex_modes_dict,
    'Edges': edges_modes_dict,
    'Faces': faces_modes_dict
    }

inputs_dict = {
    'v': 'Vertices',
    'e': 'Edges',
    'p': 'Faces',

}
socket_dict = {
    "v": "SvVerticesSocket",
    "s":"SvStringsSocket",
    "m": "SvMatrixSocket"
}
op_dict = { #signature : (prop_name, e for enum and b for boolean)
    'c': ('center_mode', 'e'),
    's': ('sum_items', 'b'),
    'o': ('origin_mode', 'e'),
    'q': ('pols_origin_mode', 'e'),
    'm': ('matrix_track', 'e'),
    'u': ('matrix_normal_up', 'e'),
    'n': ('matrix_normal', 'e'),
    't': ('tangent_mode', 'e'),
    'a': ('output_numpy', 'b'),
    'v': ('vertex_normal_mode', 'e'),
}


class SvComponentAnalyzerNode(bpy.types.Node, SverchCustomTreeNode, SvRecursiveNode):
    """
    Triggers: Center/Matrix/Length
    Tooltip: Data from vertices/edges/faces as Orientation, Location, Length, Normal, Center...

    """

    bl_idname = 'SvComponentAnalyzerNode'
    bl_label = 'Component Analyzer'
    bl_icon = 'VIEWZOOM'


    modes = [
        ('Verts', "Vertices", "Vertices Operators", 0),
        ('Edges', "Edges", "Edges Operators", 1),
        ('Faces', "Faces", "Faces Operators", 2)
    ]

    edge_modes =        [(k.replace(" ", "_"), k, descr, ident) for k, (ident, _, _, _, _, _, _, descr) in sorted(edges_modes_dict.items(),  key=lambda k: k[1][0])]
    vertex_modes =      [(k.replace(" ", "_"), k, descr, ident) for k, (ident, _, _, _, _, _, _, descr) in sorted(vertex_modes_dict.items(), key=lambda k: k[1][0])]
    face_modes =        [(k.replace(" ", "_"), k, descr, ident) for k, (ident, _, _, _, _, _, _, descr) in sorted(faces_modes_dict.items(),  key=lambda k: k[1][0])]
    pols_origin_modes = [(k.replace(" ", "_"), k, descr, ident) for k, (ident, _, descr) in sorted(pols_origin_modes_dict.items(), key=lambda k: k[1][0])]
    tangent_modes =     [(k.replace(" ", "_"), k, descr, ident) for k, (ident, _, descr) in sorted(tangent_modes_dict.items(), key=lambda k: k[1][0])]

    origin_modes = [
        ("Center", "Center", "Median Center", 0),
        ("First", "First", "First Vertex", 1),
        ("Last", "Last", "Last Vertex", 2)
    ]
    matrix_track_modes = [
        ("X", "X", "Aligned with X", 0),
        ("Y", "Y", "Aligned with Y", 1),
        ("Z", "Z", "Aligned with Z", 2),
        ("-X", "-X", "Aligned with -X", 3),
        ("-Y", "-Y", "Aligned with -Y", 4),
        ("-Z", "-Z", "Aligned with -Z", 5)
    ]
    matrix_normal_modes = [
        ("X", "X", "Aligned with X", 0),
        ("Z", "Z", "Aligned with Z", 2),
    ]
    vertex_normal_modes = [
        ('BMESH', 'Bmesh', 'Slower (Legacy)', 0),
        ('MWE', 'Mean Weighted Equally', 'Faster', 1),
        ('MWELR','Mean Weighted Edge Length Reciprocal', '', 2),
        ('MWAT', 'Mean Weighted Area Triangle', '', 3),
        ('MWS', 'Mean Weighted by Sine', '', 4)
    ]

    @throttle_and_update_node
    def update_mode(self, context):
        # for mode in self.modes:
        info = modes_dicts[self.mode][self.actual_mode().replace("_", " ")]

        input_names = info[1]
        output_socket_type = info[5]
        output_socket_name = info[6].split(', ')
        # hide unnecessary inputs only if not connected
        for input_socket, key_name in zip(self.inputs, 'vep'):
            if not input_socket.is_linked:
                if not key_name in input_names:
                    input_socket.hide_safe = True
                else:
                    input_socket.hide_safe = False

        for idx, s in enumerate(output_socket_type):
            self.outputs[idx].name = output_socket_name[idx]
            self.outputs[idx].replace_socket(socket_dict[s])
        if len(output_socket_type) < len(self.outputs):
            for s in self.outputs[len(output_socket_type):]:
                s.hide_safe = True

    mode: EnumProperty(
        name="Component",
        items=modes,
        default='Faces',
        update=update_mode)

    vertex_mode: EnumProperty(
        name="Operator",
        items=vertex_modes,
        default="Normal",
        update=update_mode)

    edge_mode: EnumProperty(
        name="Operator",
        items=edge_modes,
        default="Length",
        update=update_mode)

    face_mode: EnumProperty(
        name="Operator",
        items=face_modes,
        default="Normal",
        update=update_mode)

    flat_output: BoolProperty(
        name="Flat output",
        description="Flatten output by list-joining level 1",
        default=True,
        update=updateNode)

    split: BoolProperty(
        name="Split output",
        description="Split output",
        default=False,
        update=updateNode)

    wrap: BoolProperty(
        name="Wrap output",
        description="Wrap output",
        default=False,
        update=updateNode)

    sum_items: BoolProperty(
        name="Sum", description="Sum Items",
        default=False, update=updateNode)

    origin_mode: EnumProperty(
        name="Origin",
        items=origin_modes,
        default="Center",
        update=update_mode)

    tangent_mode: EnumProperty(
        name="Direction",
        items=tangent_modes,
        default="Edge",
        update=update_mode)

    center_mode: EnumProperty(
        name="Center",
        items=pols_origin_modes[:3],
        default="Median_Center",
        update=update_mode)

    pols_origin_mode: EnumProperty(
        name="Origin",
        items=pols_origin_modes,
        default="Median_Center",
        update=update_mode)

    vertex_normal_mode: EnumProperty(
        name="Method",
        items=vertex_normal_modes,
        default="MWE",
        update=update_mode)

    matrix_track: EnumProperty(
        name="Normal",
        items=matrix_track_modes,
        default="Z",
        update=update_mode)

    matrix_normal_up: EnumProperty(
        name="Up",
        items=matrix_track_modes,
        default="Y",
        update=update_mode)

    matrix_normal: EnumProperty(
        name="Edge",
        items=matrix_normal_modes,
        default="X",
        update=update_mode)
    output_numpy: BoolProperty(
        name='Output NumPy',
        description='Output NumPy arrays',
        default=False, update=updateNode)

    def actual_mode(self):
        if self.mode == 'Verts':
            component_mode = self.vertex_mode
        elif self.mode == 'Edges':
            component_mode = self.edge_mode
        else:
            component_mode = self.face_mode
        return component_mode

    def draw_label(self):
        if self.hide:
            text = "CA: " + self.mode + " "+ self.actual_mode()
            return self.label if self.label else text

        return  self.label if self.label else self.name

    def draw_buttons(self, context, layout):
        layout.prop(self, "mode", expand=True)
        if self.mode == 'Verts':
            layout.prop(self, "vertex_mode", text="")
        elif self.mode == 'Edges':
            layout.prop(self, "edge_mode", text="")
        elif self.mode == 'Faces':
            layout.prop(self, "face_mode", text="")
        info = modes_dicts[self.mode][self.actual_mode().replace("_", " ")]
        local_ops = info[2]
        out_ops = info[3]


        for option in local_ops:
            if option in op_dict:
                if option != 'a':
                    layout.prop(self, op_dict[option][0])

        if not 'u' in out_ops:
            layout.prop(self, 'split')
        else:
            layout.prop(self, 'wrap')

    def draw_buttons_ext(self, context, layout):
        layout.prop(self, 'list_match')
        self.draw_buttons(context, layout)
        info = modes_dicts[self.mode][self.actual_mode().replace("_", " ")]
        local_ops = info[2]
        if 'a' in local_ops:
            layout.prop(self, 'output_numpy')


    def rclick_menu(self, context, layout):
        layout.prop_menu_enum(self, "list_match", text="List Match")
        layout.prop_menu_enum(self, "mode", text=self.mode)
        if self.mode == 'Verts':
            layout.prop_menu_enum(self, "vertex_mode", text=self.vertex_mode)
        elif self.mode == 'Edges':
            layout.prop_menu_enum(self, "edge_mode", text=self.edge_mode)
        elif self.mode == 'Faces':
            layout.prop_menu_enum(self, "face_mode", text=self.face_mode)

        info = modes_dicts[self.mode][self.actual_mode().replace("_", " ")]
        local_ops = info[2]
        out_ops = info[3]
        for option in local_ops:
            if option in op_dict:
                if 'b' == op_dict[option][1]:
                    layout.prop(self, op_dict[option][0])
                else:
                    layout.prop_menu_enum(self, op_dict[option][0])
        if not 'u' in out_ops:
            layout.prop(self, 'split')
        else:
            layout.prop(self, 'wrap')

    def sv_init(self, context):
        new_input = self.inputs.new
        new_input('SvVerticesSocket', "Vertices")
        new_input('SvStringsSocket', "Edges")
        new_input('SvStringsSocket', "Faces")

        new_output = self.outputs.new
        new_output('SvStringsSocket', "Vals")
        new_output('SvVerticesSocket', "Faces")
        new_output('SvVerticesSocket', "Mask")

        self.update_mode(context)

    def post_process(self, result_vals, unwrap):
        if unwrap:
            if not self.wrap:
                return [v for r in result_vals for v in r]
        else:
            if self.split:
                return [[v] for r in result_vals for v in r]
        return result_vals

    def output(self, result_vals, socket, unwrap):
        if unwrap:
            if not self.wrap:
                result_vals = [v for r in result_vals for v in r]
        else:
            if self.split:
                result_vals = [[v] for r in result_vals for v in r]

        socket.sv_set(result_vals)
    def pre_setup(self):
        for s in self.inputs:
            s.nesting_level = 3
            s.is_mandatory = False
        modes_dict = modes_dicts[self.mode]
        component_mode = self.actual_mode().replace("_", " ")
        func_inputs = modes_dict[component_mode][1]
        if "v" in func_inputs:
            self.inputs[0].is_mandatory = True
        if "e" in func_inputs:
            self.inputs[1].is_mandatory = True
        if "p" in func_inputs:
            self.inputs[2].is_mandatory = True

    def process_data(self, params):
        verts, edges, pols = params

        modes_dict = modes_dicts[self.mode]
        component_mode = self.actual_mode().replace("_", " ")
        func_inputs, local_ops, output_ops, func, output_sockets = modes_dict[component_mode][1:6]
        params = []
        if "v" in func_inputs:
            params.append(verts)
        if "e" in func_inputs:
            params.append(edges)
        if "p" in func_inputs:
            params.append(pols)

        result_vals = []


        special = False
        if local_ops:
            options_dict = {
                'b': component_mode,
                'c': self.center_mode,
                's': self.sum_items,
                'o': self.origin_mode,
                'q': self.pols_origin_mode,
                'm': self.matrix_track,
                'u': self.matrix_normal_up,
                'n': self.matrix_normal,
                't': self.tangent_mode,
                'v': self.vertex_normal_mode,
                'a': self.output_numpy
            }
            special_op = []
            for option in local_ops:
                option_val = options_dict[option]
                special_op.append(option_val if type(option_val) == bool else option_val.replace("_", " "))
            special = True

        for param in zip(*params):
            if special:
                vals = func(*param, *special_op)
            else:
                vals = func(*param)

            result_vals.append(vals)
        unwrap = 'u' in output_ops
        if len(output_sockets) == 1:
            return self.post_process(result_vals, unwrap), [], []
        if len(output_sockets) == 2:
            return (*[self.post_process(l, unwrap) for l in zip(*result_vals)], [])

        return [self.post_process(l, unwrap) for l in zip(*result_vals)]


def register():
    bpy.utils.register_class(SvComponentAnalyzerNode)


def unregister():
    bpy.utils.unregister_class(SvComponentAnalyzerNode)
