"""Load only confirmed, TDS-verified System Templates as calculation alternatives."""
from __future__ import annotations

import json
from app.domain.models import CoatingSystem,LayerDefinition
from app.infrastructure.database.engine import get_session_factory
from app.infrastructure.database.system_template_models import SystemTemplateORM
from sqlalchemy import select
from sqlalchemy.orm import selectinload


class ConfirmedSystemTemplateService:
    """Read-only bridge from persisted confirmed templates to calculation domain."""
    def load_systems(self,materials:list) -> list[CoatingSystem]:
        material_by_id={m.id:m for m in materials if m.id is not None}
        try:
            with get_session_factory()() as session:
                stmt=(select(SystemTemplateORM).options(selectinload(SystemTemplateORM.layers)).where(SystemTemplateORM.status=="CONFIRMED",SystemTemplateORM.is_active.is_(True)).order_by(SystemTemplateORM.name))
                rows=session.scalars(stmt).unique().all()
                systems=[]
                for orm in rows:
                    metadata=json.loads(orm.metadata_json or "{}")
                    if metadata.get("tds_verified")!="KNOWN":continue
                    if not orm.source_path or not orm.source_sheet or not orm.source_sha256:continue
                    layers=[];valid=True
                    for row in sorted(orm.layers,key=lambda item:item.layer_number):
                        material=material_by_id.get(row.material_id)
                        if material is None or row.dft_target is None:valid=False;break
                        layers.append(LayerDefinition(material_id=row.material_id,material=material,layer_number=row.layer_number,dft_min=row.dft_min,dft_max=row.dft_max,target_dft=row.dft_target))
                    if not valid or not layers:continue
                    systems.append(CoatingSystem(id=orm.id,system_name=orm.name,manufacturer=orm.manufacturer or "",description=orm.description or "",substrate=orm.substrate or "",number_of_layers=len(layers),technical_document=orm.source_path,notes=(orm.notes or "")+" [CONFIRMED SYSTEM TEMPLATE; TDS VERIFIED]",layers=layers))
                return systems
        except Exception:
            return []
