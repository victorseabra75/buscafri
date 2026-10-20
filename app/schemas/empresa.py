from pydantic import BaseModel, ConfigDict


class EmpresaBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cnpj_basico: str
    razao_social: str
    nome_fantasia: str | None = None
    situacao_cadastral: str
    uf: str
    municipio: str
    cnae_fiscal_principal: str
    correio_eletronico: str | None = None
    telefone_1: str | None = None


class EmpresaResponse(BaseModel):
    total_count: int | None = None
    page: int | None = None
    limit: int
    next_cursor: str | None = None
    data: list[EmpresaBase]
