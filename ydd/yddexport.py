import bpy
from ..cwxml.drawable import DrawableDictionary
from ..ydr.ydrexport import create_drawable_xml, write_embedded_textures
from ..tools import jenkhash
from ..sollumz_properties import SollumType, SollumzExportSettings


def export_ydd(ydd_obj: bpy.types.Object, filepath: str, export_settings: SollumzExportSettings):
    ydd_xml = create_ydd_xml(ydd_obj, export_settings.auto_calculate_bone_tag)

    write_embedded_textures(ydd_obj, filepath)

    ydd_xml.write_xml(filepath)


def create_ydd_xml(ydd_obj: bpy.types.Object, auto_calc_bone_tag: bool = False):
    ydd_xml = DrawableDictionary()

    ydd_armature = find_ydd_armature(
        ydd_obj) if ydd_obj.type != "ARMATURE" else ydd_obj

    for child in ydd_obj.children:
        if child.sollum_type != SollumType.DRAWABLE:
            continue

        if child.type != "ARMATURE":
            armature_obj = ydd_armature
        else:
            armature_obj = None

        drawable_xml = create_drawable_xml(
            child, armature_obj=armature_obj, auto_calc_bone_tag=auto_calc_bone_tag)
        ydd_xml.append(drawable_xml)

    ydd_xml.sort(key=get_hash)

    return ydd_xml


def find_ydd_armature(ydd_obj: bpy.types.Object):
    """Find first drawable with an armature in ``ydd_obj``."""
    for child in ydd_obj.children:
        if child.type == "ARMATURE":
            return child


def get_hash(item):
    return jenkhash.Generate(item.name.split(".")[0])
