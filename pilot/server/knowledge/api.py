import os
import shutil
import tempfile
import logging

from fastapi import APIRouter, File, UploadFile, Form, Depends

from pilot.configs.config import Config
from pilot.configs.model_config import (
    EMBEDDING_MODEL_CONFIG,
    KNOWLEDGE_UPLOAD_ROOT_PATH,
)

from pilot.openapi.api_view_model import Result
from pilot.embedding_engine.embedding_engine import EmbeddingEngine
from pilot.embedding_engine.embedding_factory import EmbeddingFactory

from pilot.server.knowledge.service import KnowledgeService
from pilot.server.knowledge.request.request import (
    KnowledgeQueryRequest,
    KnowledgeQueryResponse,
    KnowledgeDocumentRequest,
    DocumentSyncRequest,
    ChunkQueryRequest,
    DocumentQueryRequest,
    SpaceArgumentRequest,
)

from pilot.server.knowledge.request.request import KnowledgeSpaceRequest
from pilot.user import UserRequest, get_user_from_headers

logger = logging.getLogger(__name__)

CFG = Config()
router = APIRouter()


knowledge_space_service = KnowledgeService()


@router.post("/knowledge/space/add")
def space_add(request: KnowledgeSpaceRequest, user_token: UserRequest = Depends(get_user_from_headers)):
    print(f"/space/add params: {request}")
    try:
        request.user_id = user_token.user_id
        knowledge_space_service.create_knowledge_space(request)
        return Result.succ([])
    except Exception as e:
        return Result.faild(code="E000X", msg=f"space add error {e}")


@router.post("/knowledge/space/list")
def space_list(request: KnowledgeSpaceRequest, user_token: UserRequest = Depends(get_user_from_headers)):
    print(f"/space/list params:")
    try:
        request.user_id = user_token.user_id
        return Result.succ(knowledge_space_service.get_knowledge_space(request))
    except Exception as e:
        return Result.faild(code="E000X", msg=f"space list error {e}")


@router.post("/knowledge/space/delete")
def space_delete(request: KnowledgeSpaceRequest, user_token: UserRequest = Depends(get_user_from_headers)):
    spaces = knowledge_space_service.get_knowledge_space(
        KnowledgeSpaceRequest(user_id=user_token.user_id, name=request.name))
    if len(spaces) == 0:
        return Result.faild(code="E000X",
                            msg=f"knowledge_space {request.name} can not be found by user {user_token.user_id}")
    print(f"/space/delete params:")
    try:
        return Result.succ(knowledge_space_service.delete_space(spaces[0].id))
    except Exception as e:
        return Result.faild(code="E000X", msg=f"space list error {e}")


@router.post("/knowledge/{space_name}/arguments")
def arguments(space_name: str, user_token: UserRequest = Depends(get_user_from_headers)):
    print(f"/knowledge/space/arguments params:")
    try:
        return Result.succ(knowledge_space_service.arguments(space_name, user_token.user_id))
    except Exception as e:
        return Result.faild(code="E000X", msg=f"space list error {e}")


@router.post("/knowledge/{space_name}/argument/save")
def arguments_save(space_name: str, argument_request: SpaceArgumentRequest, user_token: UserRequest = Depends(get_user_from_headers)):
    print(f"/knowledge/space/argument/save params:")
    try:
        return Result.succ(
            knowledge_space_service.argument_save(space_name, argument_request, user_token.user_id)
        )
    except Exception as e:
        return Result.faild(code="E000X", msg=f"space list error {e}")


@router.post("/knowledge/{space_name}/document/add")
def document_add(space_name: str, request: KnowledgeDocumentRequest, user_token: UserRequest = Depends(get_user_from_headers)):
    spaces = knowledge_space_service.get_knowledge_space(KnowledgeSpaceRequest(user_id=user_token.user_id, name=space_name))
    if len(spaces) == 0:
        return Result.faild(code="E000X", msg=f"knowledge_space {space_name} can not be found by user {user_token.user_id}")

    print(f"/document/add params: {space_name}, {request}, {user_token.user_id}")
    try:
        return Result.succ(
            knowledge_space_service.create_knowledge_document(
                space_id=spaces[0].id, request=request
            )
        )
    except Exception as e:
        return Result.faild(code="E000X", msg=f"document add error {e}")


@router.post("/knowledge/{space_name}/document/list")
def document_list(space_name: str, query_request: DocumentQueryRequest, user_token: UserRequest = Depends(get_user_from_headers)):
    spaces = knowledge_space_service.get_knowledge_space(
        KnowledgeSpaceRequest(user_id=user_token.user_id, name=space_name))
    if len(spaces) == 0:
        return Result.faild(code="E000X",
                            msg=f"knowledge_space {space_name} can not be found by user {user_token.user_id}")
    print(f"/document/list params: {space_name}, {query_request}")
    try:
        return Result.succ(
            knowledge_space_service.get_knowledge_documents(spaces[0].id, query_request)
        )
    except Exception as e:
        return Result.faild(code="E000X", msg=f"document list error {e}")


@router.post("/knowledge/{space_name}/document/delete")
def document_delete(space_name: str, query_request: DocumentQueryRequest, user_token: UserRequest = Depends(get_user_from_headers)):
    spaces = knowledge_space_service.get_knowledge_space(
        KnowledgeSpaceRequest(user_id=user_token.user_id, name=space_name))
    if len(spaces) == 0:
        return Result.faild(code="E000X",
                            msg=f"knowledge_space {space_name} can not be found by user {user_token.user_id}")
    print(f"/document/list params: {space_name}, {query_request}")
    try:
        return Result.succ(
            knowledge_space_service.delete_document(spaces[0].id, query_request.doc_name)
        )
    except Exception as e:
        return Result.faild(code="E000X", msg=f"document list error {e}")


@router.post("/knowledge/{space_name}/document/upload")
async def document_upload(
    space_name: str,
    doc_name: str = Form(...),
    doc_type: str = Form(...),
    doc_file: UploadFile = File(...),
    user_token: UserRequest = Depends(get_user_from_headers)
):
    spaces = knowledge_space_service.get_knowledge_space(
        KnowledgeSpaceRequest(user_id=user_token.user_id, name=space_name))
    if len(spaces) == 0:
        return Result.faild(code="E000X",
                            msg=f"knowledge_space {space_name} can not be found by user {user_token.user_id}")
    print(f"/document/upload params: {space_name}")
    try:
        space_name_dir = space_name + user_token.user_id
        if doc_file:
            if not os.path.exists(os.path.join(KNOWLEDGE_UPLOAD_ROOT_PATH, space_name_dir)):
                os.makedirs(os.path.join(KNOWLEDGE_UPLOAD_ROOT_PATH, space_name_dir))
            # We can not move temp file in windows system when we open file in context of `with`
            tmp_fd, tmp_path = tempfile.mkstemp(
                dir=os.path.join(KNOWLEDGE_UPLOAD_ROOT_PATH, space_name_dir)
            )
            with os.fdopen(tmp_fd, "wb") as tmp:
                tmp.write(await doc_file.read())
            shutil.move(
                tmp_path,
                os.path.join(KNOWLEDGE_UPLOAD_ROOT_PATH, space_name_dir, doc_file.filename),
            )
            request = KnowledgeDocumentRequest()
            request.doc_name = doc_name
            request.doc_type = doc_type
            request.content = os.path.join(
                KNOWLEDGE_UPLOAD_ROOT_PATH, space_name_dir, doc_file.filename
            )
            return Result.succ(
                knowledge_space_service.create_knowledge_document(
                    space_id=spaces[0].id, request=request
                )
            )
            # return Result.succ([])
        return Result.faild(code="E000X", msg=f"doc_file is None")
    except Exception as e:
        return Result.faild(code="E000X", msg=f"document add error {e}")


@router.post("/knowledge/{space_name}/document/sync")
def document_sync(space_name: str, request: DocumentSyncRequest, user_token: UserRequest = Depends(get_user_from_headers)):
    spaces = knowledge_space_service.get_knowledge_space(
        KnowledgeSpaceRequest(user_id=user_token.user_id, name=space_name))
    if len(spaces) == 0:
        return Result.faild(code="E000X",
                            msg=f"knowledge_space {space_name} can not be found by user {user_token.user_id}")
    logger.info(f"Received params: {space_name}, {request}")
    try:
        knowledge_space_service.sync_knowledge_document(
            space_id=spaces[0].id, sync_request=request, user_id=user_token.user_id,
        )
        return Result.succ([])
    except Exception as e:
        return Result.faild(code="E000X", msg=f"document sync error {e}")


@router.post("/knowledge/{space_name}/chunk/list")
def document_list(space_name: str, query_request: ChunkQueryRequest, user_token: UserRequest = Depends(get_user_from_headers)):
    print(f"/document/list params: {space_name}, {query_request}")
    try:
        return Result.succ(knowledge_space_service.get_document_chunks(query_request))
    except Exception as e:
        return Result.faild(code="E000X", msg=f"document chunk list error {e}")


@router.post("/knowledge/{vector_name}/query")
def similar_query(space_name: str, query_request: KnowledgeQueryRequest, user_token: UserRequest = Depends(get_user_from_headers)):
    print(f"Received params: {space_name}, {query_request}")
    embedding_factory = CFG.SYSTEM_APP.get_component(
        "embedding_factory", EmbeddingFactory
    )
    client = EmbeddingEngine(
        model_name=EMBEDDING_MODEL_CONFIG[CFG.EMBEDDING_MODEL],
        vector_store_config={"vector_store_name": space_name + user_token.user_id},
        embedding_factory=embedding_factory,
    )
    docs = client.similar_search(query_request.query, query_request.top_k)
    res = [
        KnowledgeQueryResponse(text=d.page_content, source=d.metadata["source"])
        for d in docs
    ]
    return {"response": res}
