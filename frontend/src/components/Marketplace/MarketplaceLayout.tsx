import React from 'react';
import { Outlet, NavLink } from 'react-router-dom';
import { Package, Cpu, Leaf } from 'lucide-react';

export const MarketplaceLayout: React.FC = () => {
  return (
    <div className="space-y-6 max-w-[1200px] mx-auto animate-fade-in pb-12">
      {/* Shared Marketplace Spine Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-[0.05em] flex items-center gap-3">
            <Package className="text-[var(--orange)]" size={24} />
            MARKETPLACE
          </h1>
          <p className="text-sm text-[var(--text-secondary)] mt-2 max-w-2xl">
            Veklom marketplace packages SDKs, IDE plugins, CI controls, and premium vertical runtime add-ons.
          </p>
        </div>
      </div>

      {/* Shared Marketplace Navigation */}
      <div className="flex border-b border-[rgba(255,255,255,0.05)] overflow-x-auto no-scrollbar gap-2 pb-[-1px]">
        <NavLink
          to="/marketplace"
          end
          className={({ isActive }) =>
            `px-6 py-3 text-sm font-semibold whitespace-nowrap border-b-2 transition-colors flex items-center gap-2 ${
              isActive
                ? 'border-[var(--orange)] text-white'
                : 'border-transparent text-[var(--text-muted)] hover:text-white'
            }`
          }
        >
          <Package size={16} />
          Catalog
        </NavLink>
        <NavLink
          to="/marketplace/irongrid"
          className={({ isActive }) =>
            `px-6 py-3 text-sm font-semibold whitespace-nowrap border-b-2 transition-colors flex items-center gap-2 ${
              isActive
                ? 'border-[var(--orange)] text-white'
                : 'border-transparent text-[var(--text-muted)] hover:text-white'
            }`
          }
        >
          <Cpu size={16} />
          IronGrid Mesh
        </NavLink>
        <NavLink
          to="/marketplace/greenvision"
          className={({ isActive }) =>
            `px-6 py-3 text-sm font-semibold whitespace-nowrap border-b-2 transition-colors flex items-center gap-2 ${
              isActive
                ? 'border-emerald-500 text-white'
                : 'border-transparent text-[var(--text-muted)] hover:text-white'
            }`
          }
        >
          <Leaf size={16} className="text-emerald-500" />
          GreenVision
        </NavLink>
      </div>

      {/* Content Outlet */}
      <div className="pt-4">
        <Outlet />
      </div>
    </div>
  );
};
