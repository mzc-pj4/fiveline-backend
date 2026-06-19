from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException

from app.deps import CurrentUser, require_admin

router = APIRouter(prefix="/api/admin/cicd", tags=["cicd"])

NAMESPACE = "fiveline"


def _get_custom_api() -> client.CustomObjectsApi:
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()
    return client.CustomObjectsApi()


class RolloutActionRequest(BaseModel):
    service_name: str
    action: str  # "promote" | "abort"


@router.post("/rollout-action")
def rollout_action(
    _: Annotated[CurrentUser, Depends(require_admin)],
    body: RolloutActionRequest,
):
    if body.action == "promote":
        patch = {
            "metadata": {
                "annotations": {
                    "argoproj.io/manual-gate-passed": "true"
                }
            }
        }
    elif body.action == "abort":
        patch = {"spec": {"abort": True}}
    else:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 액션: {body.action}")

    try:
        _get_custom_api().patch_namespaced_custom_object(
            group="argoproj.io",
            version="v1alpha1",
            namespace=NAMESPACE,
            plural="rollouts",
            name=body.service_name,
            body=patch,
        )
    except ApiException as e:
        raise HTTPException(status_code=e.status, detail=e.reason)

    return {"status": "ok", "action": body.action, "service": body.service_name}
