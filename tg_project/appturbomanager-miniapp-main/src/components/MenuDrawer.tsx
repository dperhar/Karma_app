import { X } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

interface MenuDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

export const MenuDrawer = ({ isOpen, onClose }: MenuDrawerProps) => {
  const pathname = usePathname();

  const menuItems = [
    { href: '/', label: 'Главная' },
    { href: '/booking', label: 'Бронирование' },
    { href: '/pool-matches', label: 'Матчи' },
    { href: '/dating', label: 'Знакомства' },
    { href: '/leaderboard', label: 'Таблица лидеров' },
    { href: '/shop', label: 'Магазин' },
    { href: '/tournaments', label: 'Турниры' },
    { href: '/profile', label: 'Профиль' },
  ];

  return (
    <>
      {/* Overlay */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-brand-black bg-opacity-50 z-40"
          onClick={onClose}
        />
      )}

      {/* Drawer */}
      <div 
        className={`fixed top-0 left-0 h-full w-64 bg-base-100 shadow-lg transform transition-transform duration-300 ease-in-out z-50 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-base-300 bg-brand-blue text-white">
          <h2 className="text-lg font-semibold">Меню</h2>
          <button
            onClick={onClose}
            className="btn btn-ghost btn-sm btn-circle text-white"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Menu Items */}
        <nav className="p-4">
          <ul className="space-y-2">
            {menuItems.map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  onClick={onClose}
                  className={`menu-item ${
                    pathname === item.href
                      ? 'menu-item-active'
                      : 'menu-item-inactive'
                  }`}
                >
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </div>
    </>
  );
}; 