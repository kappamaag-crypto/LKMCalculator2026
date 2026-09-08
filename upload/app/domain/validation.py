"""Валидация входных данных и результатов расчёта."""
from __future__ import annotations
from dataclasses import dataclass,field
from typing import Optional,Sequence
from app.domain.models import Material,LayerDefinition,LayerResult,CoatingSystem,ObjectData
from app.domain.enums import CompatibilityStatus
from app.domain.formulas import DILUTION_BASIS_BY_PAINT_VOLUME,DILUTION_BASIS_BY_MIX_VOLUME,DILUTION_BASIS_BY_MASS,DILUTION_BASIS_BY_COMPONENT_VOLUME
VALID_THINNER_BASES={DILUTION_BASIS_BY_PAINT_VOLUME,DILUTION_BASIS_BY_MIX_VOLUME,DILUTION_BASIS_BY_MASS,DILUTION_BASIS_BY_COMPONENT_VOLUME}
@dataclass
class ValidationIssue:
    level:str; code:str; message:str; field:Optional[str]=None; layer_index:Optional[int]=None
@dataclass
class ValidationResult:
    issues:list[ValidationIssue]=field(default_factory=list)
    @property
    def has_errors(self): return any(i.level=="error" for i in self.issues)
    @property
    def has_warnings(self): return any(i.level=="warning" for i in self.issues)
    @property
    def errors(self): return [i for i in self.issues if i.level=="error"]
    @property
    def warnings(self): return [i for i in self.issues if i.level=="warning"]
    def add_error(self,code,message,field=None,layer_index=None): self.issues.append(ValidationIssue("error",code,message,field,layer_index))
    def add_warning(self,code,message,field=None,layer_index=None): self.issues.append(ValidationIssue("warning",code,message,field,layer_index))
    def add_info(self,code,message,field=None,layer_index=None): self.issues.append(ValidationIssue("info",code,message,field,layer_index))
    def merge(self,other): self.issues.extend(other.issues)
def _range(result,minimum,maximum,code,message,field):
    if minimum is not None and maximum is not None and minimum>maximum: result.add_error(code,message,field)
def validate_material(material:Material)->ValidationResult:
    r=ValidationResult()
    if not material.material_name or not material.material_name.strip(): r.add_error("MAT_NAME","Не указано название материала","material_name")
    if material.density is None: r.add_error("MAT_DENSITY_UNKNOWN","Плотность материала неизвестна — расчёт массы в кг невозможен","density")
    elif material.density<=0: r.add_error("MAT_DENSITY_INVALID","Плотность материала должна быть больше нуля","density")
    if material.solids_by_volume_percent is None:
        if material.solids_percent is None: r.add_error("MAT_SOLIDS_UNKNOWN","Объёмная доля сухого остатка неизвестна — инженерный расчёт WFT невозможен","solids_by_volume_percent")
        elif material.solids_percent<=0 and material.material_type.value!="разбавитель": r.add_error("MAT_SOLIDS_ZERO","Сухой остаток равен 0 % — расчёт WFT невозможен","solids_percent")
        else: r.add_warning("MAT_SOLIDS_BASIS_LEGACY","Объёмная доля сухого остатка не указана; расчёт использует legacy-поле «solids_percent». Проверьте базу значения по TDS.","solids_by_volume_percent")
    else:
        if material.solids_by_volume_percent<0: r.add_error("MAT_SV_LT0","Сухой остаток по объёму не может быть отрицательным","solids_by_volume_percent")
        elif material.solids_by_volume_percent>100: r.add_error("MAT_SV_GT100","Сухой остаток по объёму не может превышать 100 %","solids_by_volume_percent")
        elif material.solids_by_volume_percent==0 and material.material_type.value!="разбавитель": r.add_error("MAT_SV_ZERO","Сухой остаток по объёму равен 0 % — расчёт WFT невозможен","solids_by_volume_percent")
    if material.solids_percent is not None:
        if material.solids_percent<0: r.add_error("MAT_SOLIDS_LT0","Сухой остаток не может быть отрицательным","solids_percent")
        elif material.solids_percent>100: r.add_error("MAT_SOLIDS_GT100","Сухой остаток не может превышать 100 %","solids_percent")
    if material.price_per_kg is not None and material.price_per_kg<0: r.add_error("MAT_PRICE_NEG","Цена не может быть отрицательной","price_per_kg")
    if material.price_per_liter is not None and material.price_per_liter<0: r.add_error("MAT_PRICE_L_NEG","Цена за литр не может быть отрицательной","price_per_liter")
    _range(r,material.min_application_temperature,material.max_application_temperature,"MAT_TEMP_RANGE","Диапазон температуры нанесения задан некорректно","application_temperature")
    _range(r,material.min_recoat_time_h,material.max_recoat_time_h,"MAT_RECOAT_RANGE","Диапазон межслойной выдержки задан некорректно","recoat_time_h")
    if material.max_relative_humidity is not None and not 0<=material.max_relative_humidity<=100: r.add_error("MAT_RH_MAX_RANGE","Максимальная относительная влажность должна быть в диапазоне 0–100 %","max_relative_humidity")
    if material.min_dew_point_margin_c is not None and material.min_dew_point_margin_c<0: r.add_error("MAT_DEW_MARGIN_NEG","Минимальный запас до точки росы не может быть отрицательным","min_dew_point_margin_c")
    if material.recommended_dft_min is not None and material.recommended_dft_min<0: r.add_error("MAT_DFT_MIN_NEG","Минимальная рекомендуемая толщина не может быть отрицательной","recommended_dft_min")
    if material.recommended_dft_max is not None and material.recommended_dft_max<0: r.add_error("MAT_DFT_MAX_NEG","Максимальная рекомендуемая толщина не может быть отрицательной","recommended_dft_max")
    if material.max_single_layer_dft is not None and material.max_single_layer_dft<=0: r.add_error("MAT_DFT_SINGLE_INVALID","Максимальная толщина одного слоя должна быть больше нуля","max_single_layer_dft")
    if material.recommended_dft_min is not None and material.recommended_dft_max is not None and material.recommended_dft_min>material.recommended_dft_max: r.add_error("MAT_DFT_RANGE","Минимальная рекомендуемая толщина больше максимальной","recommended_dft")
    if material.thinner_percent_min is not None and material.thinner_percent_min<0: r.add_error("MAT_THINNER_MIN_NEG","Минимальный процент разбавителя не может быть отрицательным","thinner_percent_min")
    if material.thinner_percent_max is not None and material.thinner_percent_max<0: r.add_error("MAT_THINNER_MAX_NEG","Максимальный процент разбавителя не может быть отрицательным","thinner_percent_max")
    if material.thinner_percent_min is not None and material.thinner_percent_max is not None and material.thinner_percent_min>material.thinner_percent_max: r.add_error("MAT_THINNER_RANGE","Минимальный процент разбавителя больше максимального","thinner_percent")
    if material.thinner_basis not in VALID_THINNER_BASES: r.add_error("MAT_THINNER_BASIS",f"Неизвестная база расчёта разбавления: «{material.thinner_basis}»","thinner_basis")
    return r
def validate_layer_input(material:Material,target_dft:float,losses_percent:float=0.0,thinner_percent:float=0.0,layer_index:int|None=None,thinner_basis:str|None=None)->ValidationResult:
    r=ValidationResult(); mr=validate_material(material)
    for i in mr.issues: i.layer_index=layer_index; r.issues.append(i)
    if target_dft<0: r.add_error("LAYER_DFT_NEG","Толщина сухого слоя не может быть отрицательной","target_dft",layer_index)
    if target_dft==0: r.add_warning("LAYER_DFT_ZERO","Толщина сухого слоя равна нулю","target_dft",layer_index)
    if losses_percent<0: r.add_error("LAYER_LOSSES_NEG","Потери не могут быть отрицательными","losses_percent",layer_index)
    if losses_percent>=100: r.add_error("LAYER_LOSSES_GE100","Потери не могут быть ≥ 100 %","losses_percent",layer_index)
    if thinner_percent<0: r.add_error("LAYER_THINNER_NEG","Процент разбавителя не может быть отрицательным","thinner_percent",layer_index)
    if thinner_percent>=100: r.add_error("LAYER_THINNER_GE100","Процент разбавителя должен быть меньше 100 %","thinner_percent",layer_index)
    basis=thinner_basis or material.thinner_basis
    if basis not in VALID_THINNER_BASES: r.add_error("LAYER_THINNER_BASIS",f"Неизвестная база разбавления: «{basis}»","thinner_basis",layer_index)
    if material.thinner_required and thinner_percent<=0: r.add_warning("LAYER_THINNER_REQUIRED",f"Для «{material.material_name}» указан обязательный разбавитель, но процент разбавления не задан","thinner_percent",layer_index)
    if material.thinner_percent_min is not None and thinner_percent<material.thinner_percent_min: r.add_warning("LAYER_THINNER_BELOW_MIN",f"Разбавление {thinner_percent:g} % ниже рекомендованного минимума {material.thinner_percent_min:g} %","thinner_percent",layer_index)
    if material.thinner_percent_max is not None and thinner_percent>material.thinner_percent_max: r.add_error("LAYER_THINNER_ABOVE_MAX",f"Разбавление {thinner_percent:g} % превышает допустимый максимум {material.thinner_percent_max:g} %","thinner_percent",layer_index)
    if basis==DILUTION_BASIS_BY_MIX_VOLUME and thinner_percent>=100: r.add_error("LAYER_MIX_DILUTION_INVALID","При расчёте разбавления как доли конечной смеси процент должен быть меньше 100 %","thinner_percent",layer_index)
    if material.recommended_dft_min is not None and target_dft>0 and target_dft<material.recommended_dft_min: r.add_warning("LAYER_DFT_BELOW_MIN",f"Толщина {target_dft} мкм ниже рекомендуемого минимума ({material.recommended_dft_min} мкм) для «{material.material_name}»","target_dft",layer_index)
    if material.recommended_dft_max is not None and target_dft>0 and target_dft>material.recommended_dft_max: r.add_warning("LAYER_DFT_ABOVE_MAX",f"Толщина {target_dft} мкм выше рекомендуемого максимума ({material.recommended_dft_max} мкм) для «{material.material_name}»","target_dft",layer_index)
    if material.max_single_layer_dft is not None and target_dft>material.max_single_layer_dft: r.add_error("LAYER_DFT_MAX_SINGLE",f"Толщина {target_dft} мкм превышает максимальную толщину одного слоя ({material.max_single_layer_dft} мкм) для «{material.material_name}»","target_dft",layer_index)
    return r
def validate_application_conditions(obj:ObjectData,material:Material,layer_index:int|None=None)->ValidationResult:
    r=ValidationResult(); temperature=obj.surface_temperature if obj.surface_temperature is not None else obj.air_temperature
    if temperature is not None:
        if material.min_application_temperature is not None and temperature<material.min_application_temperature: r.add_error("COND_TEMP_BELOW_MIN",f"Температура {temperature:g} °C ниже минимальной для «{material.material_name}» ({material.min_application_temperature:g} °C)","surface_temperature",layer_index)
        if material.max_application_temperature is not None and temperature>material.max_application_temperature: r.add_error("COND_TEMP_ABOVE_MAX",f"Температура {temperature:g} °C выше максимальной для «{material.material_name}» ({material.max_application_temperature:g} °C)","surface_temperature",layer_index)
    if obj.relative_humidity is not None and material.max_relative_humidity is not None and obj.relative_humidity>material.max_relative_humidity: r.add_error("COND_RH_ABOVE_MAX",f"Относительная влажность {obj.relative_humidity:g} % превышает допустимую для «{material.material_name}» ({material.max_relative_humidity:g} %)","relative_humidity",layer_index)
    if obj.surface_temperature is not None and obj.dew_point is not None:
        margin=obj.surface_temperature-obj.dew_point
        if material.min_dew_point_margin_c is None: r.add_warning("COND_DEW_MARGIN_UNKNOWN",f"Минимальный запас до точки росы для «{material.material_name}» не указан — автоматическая проверка запаса невозможна","dew_point_margin_c",layer_index)
        elif margin<material.min_dew_point_margin_c: r.add_error("COND_DEW_MARGIN",f"Запас температуры поверхности до точки росы {margin:.1f} °C меньше требуемого {material.min_dew_point_margin_c:.1f} °C для «{material.material_name}»","dew_point_margin_c",layer_index)
    return r
def validate_object_data(obj:ObjectData)->ValidationResult:
    r=ValidationResult()
    if obj.area_m2<0: r.add_error("OBJ_AREA_NEG","Площадь не может быть отрицательной","area_m2")
    if obj.area_m2==0 and obj.area_per_element<=0: r.add_warning("OBJ_AREA_ZERO","Площадь равна нулю — итоговые количества будут нулевыми","area_m2")
    if obj.elements_count<0: r.add_error("OBJ_ELEMENTS_NEG","Количество элементов не может быть отрицательным","elements_count")
    if obj.area_per_element<0: r.add_error("OBJ_AREA_PER_EL_NEG","Площадь элемента не может быть отрицательной","area_per_element")
    if obj.temperature_min is not None and obj.temperature_max is not None and obj.temperature_min>obj.temperature_max: r.add_error("OBJ_TEMP_RANGE","Минимальная температура объекта больше максимальной","temperature_range")
    if obj.relative_humidity is not None and not 0<=obj.relative_humidity<=100: r.add_error("OBJ_RH_RANGE","Относительная влажность должна быть в диапазоне 0–100 %","relative_humidity")
    if obj.roughness is not None and obj.roughness<0: r.add_error("OBJ_ROUGHNESS_NEG","Шероховатость не может быть отрицательной","roughness")
    if obj.surface_temperature is not None and obj.dew_point is not None and obj.surface_temperature<=obj.dew_point: r.add_error("OBJ_DEW_POINT",f"Температура поверхности ({obj.surface_temperature} °C) не выше точки росы ({obj.dew_point} °C) — нанесение недопустимо","dew_point")
    if obj.dew_point_margin_c is not None and obj.dew_point_margin_c<0: r.add_error("OBJ_DEW_MARGIN_NEG","Запас до точки росы не может быть отрицательным","dew_point_margin_c")
    return r
def validate_system_layers(layers:Sequence[LayerDefinition|LayerResult],compatibility_checker=None,system:CoatingSystem|None=None)->ValidationResult:
    r=ValidationResult()
    if not layers: r.add_error("SYS_NO_LAYERS","Система не содержит слоёв"); return r
    prev_binder=None; total_target_dft=0.0
    for i,layer in enumerate(layers):
        if isinstance(layer,LayerResult): material=layer.material; binder=material.binder_type.value if material else ""; dft=layer.target_dft
        else: material=layer.material; binder=material.binder_type.value if material and hasattr(material.binder_type,"value") else (str(material.binder_type) if material else ""); dft=layer.target_dft
        if material is None: r.add_error("SYS_LAYER_NO_MATERIAL",f"Слой {i+1}: не указан материал",layer_index=i)
        if dft<0: r.add_error("SYS_LAYER_DFT_NEG",f"Слой {i+1}: толщина не может быть отрицательной","target_dft",i)
        else: total_target_dft+=dft
        if compatibility_checker and prev_binder and binder:
            status=compatibility_checker(prev_binder,binder)
            if status==CompatibilityStatus.FORBIDDEN.value: r.add_error("SYS_COMPAT_FORBIDDEN",f"Слои {i}/{i+1}: сочетание связующих «{prev_binder}» → «{binder}» запрещено",layer_index=i)
            elif status==CompatibilityStatus.WARNING.value: r.add_warning("SYS_COMPAT_WARNING",f"Слои {i}/{i+1}: сочетание «{prev_binder}» → «{binder}» требует проверки",layer_index=i)
            elif status==CompatibilityStatus.UNKNOWN.value: r.add_info("SYS_COMPAT_UNKNOWN",f"Слои {i}/{i+1}: нет подтвержденных данных о совместимости",layer_index=i)
        if binder: prev_binder=binder
    if system:
        if system.number_of_layers and system.number_of_layers!=len(layers): r.add_error("SYS_LAYER_COUNT",f"Система требует {system.number_of_layers} слоёв, задано {len(layers)}","number_of_layers")
        if system.total_dft_min is not None and total_target_dft<system.total_dft_min: r.add_error("SYS_TOTAL_DFT_BELOW_MIN",f"Суммарная DFT {total_target_dft:g} мкм ниже минимума системы {system.total_dft_min:g} мкм","total_dft")
        if system.total_dft_max is not None and total_target_dft>system.total_dft_max: r.add_error("SYS_TOTAL_DFT_ABOVE_MAX",f"Суммарная DFT {total_target_dft:g} мкм выше максимума системы {system.total_dft_max:g} мкм","total_dft")
    return r
def validate_before_calculation(obj:ObjectData,layers:Sequence[tuple[Material,float,float,float]],compatibility_checker=None,system:CoatingSystem|None=None)->ValidationResult:
    r=validate_object_data(obj); defs=[]
    for i,(material,dft,losses,thinner) in enumerate(layers):
        r.merge(validate_layer_input(material,dft,losses,thinner,i)); r.merge(validate_application_conditions(obj,material,i)); defs.append(LayerDefinition(material=material,target_dft=dft,losses_percent=losses,thinner_percent=thinner))
    r.merge(validate_system_layers(defs,compatibility_checker,system=system)); return r
