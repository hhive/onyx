"use client";

import { useState, useEffect } from "react";
import { Button } from "@opal/components";
import { useProjectsContext } from "@/providers/ProjectsContext";
import { useKeyPress } from "@/hooks/useKeyPress";
import { InputVertical } from "@opal/layouts";
import { useAppRouter } from "@/hooks/appNavigation";
import { useModal } from "@/refresh-components/contexts/ModalContext";
import { SvgFolderPlus } from "@opal/icons";
import Modal from "@/refresh-components/Modal";
import InputTypeIn from "@/refresh-components/inputs/InputTypeIn";
import { toast } from "@/hooks/useToast";

interface CreateProjectModalProps {
  initialProjectName?: string;
}

export default function CreateProjectModal({
  initialProjectName,
}: CreateProjectModalProps) {
  const { createProject } = useProjectsContext();
  const modal = useModal();
  const route = useAppRouter();
  const [projectName, setProjectName] = useState(initialProjectName ?? "");

  // Reset when prop changes (modal reopens with different value)
  useEffect(() => {
    setProjectName(initialProjectName ?? "");
  }, [initialProjectName]);

  async function handleSubmit() {
    const name = projectName.trim();
    if (!name) return;

    try {
      const newProject = await createProject(name);
      route({ projectId: newProject.id });
      modal.toggle(false);
    } catch (e) {
      toast.error(`创建项目 ${name} 失败`);
    }
  }

  useKeyPress(handleSubmit, "Enter");

  return (
    <>
      <Modal open={modal.isOpen} onOpenChange={modal.toggle}>
        <Modal.Content width="sm">
          <Modal.Header
            icon={SvgFolderPlus}
            title="新建项目"
            description="用项目集中整理文件和聊天，并为持续工作添加自定义指令。"
            onClose={() => modal.toggle(false)}
          />
          <Modal.Body>
            <InputVertical title="项目名称" withLabel>
              <InputTypeIn
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                placeholder="你正在做什么？"
                showClearButton
              />
            </InputVertical>
          </Modal.Body>
          <Modal.Footer>
            <Button prominence="secondary" onClick={() => modal.toggle(false)}>
              取消
            </Button>
            <Button disabled={!projectName.trim()} onClick={handleSubmit}>
              创建项目
            </Button>
          </Modal.Footer>
        </Modal.Content>
      </Modal>
    </>
  );
}
