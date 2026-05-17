export const GREETING_MESSAGES = ["有什么可以帮你？", "我们开始吧。"];

export function getRandomGreeting(): string {
  return GREETING_MESSAGES[
    Math.floor(Math.random() * GREETING_MESSAGES.length)
  ] as string;
}
