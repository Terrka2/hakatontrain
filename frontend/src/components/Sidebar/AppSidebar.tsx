import {
  ClipboardList,
  ListOrdered,
  Map as MapIcon,
  Route as RouteIcon,
  Users,
} from "lucide-react"

import { SidebarAppearance } from "@/components/Common/Appearance"
import { Logo } from "@/components/Common/Logo"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
} from "@/components/ui/sidebar"
import useAuth from "@/hooks/useAuth"
import { type Item, Main } from "./Main"
import { User } from "./User"

// ЗАМОРОЖЕНО после C0: пункты меню всех экранов ядра уже есть. Экраны наполняют блоки F1–F5.
const supervisorItems: Item[] = [
  { icon: MapIcon, title: "Карта", path: "/" },
  { icon: ListOrdered, title: "Очередь", path: "/queue" },
  { icon: RouteIcon, title: "План и бригады", path: "/plan" },
]

const crewItems: Item[] = [
  { icon: ClipboardList, title: "Мой маршрут", path: "/crew" },
]

export function AppSidebar() {
  const { user: currentUser } = useAuth()

  const roleItems =
    currentUser?.role === "supervisor"
      ? supervisorItems
      : currentUser?.role === "crew"
        ? crewItems
        : []
  const items = currentUser?.is_superuser
    ? [
        ...supervisorItems,
        ...crewItems,
        { icon: Users, title: "Admin", path: "/admin" },
      ]
    : roleItems

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="px-4 py-6 group-data-[collapsible=icon]:px-0 group-data-[collapsible=icon]:items-center">
        <Logo variant="responsive" />
      </SidebarHeader>
      <SidebarContent>
        <Main items={items} />
      </SidebarContent>
      <SidebarFooter>
        <SidebarAppearance />
        <User user={currentUser} />
      </SidebarFooter>
    </Sidebar>
  )
}

export default AppSidebar
