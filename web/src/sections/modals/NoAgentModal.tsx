"use client";

import Modal from "@/refresh-components/Modal";
import { Button } from "@opal/components";
import Text from "@/refresh-components/texts/Text";
import { useUser } from "@/providers/UserProvider";
import { SvgUser } from "@opal/icons";

export default function NoAgentModal() {
  const { isAdmin } = useUser();

  return (
    <Modal open>
      <Modal.Content width="sm" height="sm">
        <Modal.Header icon={SvgUser} title="暂无可用智能体" />
        <Modal.Body>
          <Text as="p">
            当前没有已配置的智能体。需要先完成配置后才能使用此功能。
          </Text>
          {isAdmin ? (
            <>
              <Text as="p">
                你是管理员，可以前往管理面板创建新的智能体。
              </Text>
              <Button width="full" href="/admin/agents">
                前往管理面板
              </Button>
            </>
          ) : (
            <Text as="p">
              请联系管理员为你配置智能体。
            </Text>
          )}
        </Modal.Body>
      </Modal.Content>
    </Modal>
  );
}
