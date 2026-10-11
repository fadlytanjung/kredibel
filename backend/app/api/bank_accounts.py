"""Bank account routes; numbers in, masks out (AC-013-14, docs/14 §6)."""

from typing import Any

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import ServiceProvider, org_of
from app.core.auth import Principal, PrincipalDependency
from app.domain.models.workspace import BankAccount, BankAccountCreate, BankAccountUpdate


def _body(account: BankAccount) -> dict[str, Any]:
    return account.model_dump(by_alias=True, exclude_none=True)


def create_bank_accounts_router(
    provider: ServiceProvider, workspace_dep: PrincipalDependency
) -> APIRouter:
    router = APIRouter(prefix="/api/bank-accounts", tags=["workspace"])

    @router.get("")
    async def list_accounts(principal: Principal = Depends(workspace_dep)) -> dict[str, Any]:
        accounts = await provider.workspace_service.list_bank_accounts(org_of(principal))
        return {"items": [_body(a) for a in accounts]}

    @router.post("", status_code=status.HTTP_201_CREATED)
    async def add_account(
        body: BankAccountCreate, principal: Principal = Depends(workspace_dep)
    ) -> dict[str, Any]:
        account = await provider.workspace_service.add_bank_account(
            principal, org_of(principal), body
        )
        return _body(account)

    @router.patch("/{account_id}")
    async def update_account(
        account_id: str, body: BankAccountUpdate, principal: Principal = Depends(workspace_dep)
    ) -> dict[str, Any]:
        account = await provider.workspace_service.update_bank_account(
            org_of(principal), account_id, body
        )
        return _body(account)

    @router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_account(
        account_id: str, principal: Principal = Depends(workspace_dep)
    ) -> Response:
        await provider.workspace_service.delete_bank_account(org_of(principal), account_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router
