import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { 
  Search, 
  Filter, 
  ShoppingCart, 
  Star, 
  Download, 
  ExternalLink,
  Shield,
  Zap,
  Globe,
  Database,
  Lock,
  TrendingUp,
  DollarSign,
  Package,
  ChevronDown
} from 'lucide-react';

interface MarketplaceListing {
  id: string;
  vendor_id: string;
  name: string;
  description: string;
  category: string;
  price: number;
  pricing_model: string;
  icon_url: string;
  status: string;
  tags: string[];
  downloads: number;
  rating: number;
  created_at: string;
  updated_at: string;
}

interface Vendor {
  id: string;
  business_name: string;
  status: string;
  total_revenue: number;
}

const CATEGORIES = [
  { value: 'all', label: 'All Categories', icon: Package },
  { value: 'security', label: 'Security', icon: Shield },
  { value: 'privacy', label: 'Privacy', icon: Lock },
  { value: 'devops', label: 'DevOps', icon: Zap },
  { value: 'monitoring', label: 'Monitoring', icon: TrendingUp },
  { value: 'infrastructure', label: 'Infrastructure', icon: Globe },
  { value: 'data', label: 'Data', icon: Database },
  { value: 'automation', label: 'Automation', icon: Zap },
  { value: 'development', label: 'Development', icon: Package },
  { value: 'compliance', label: 'Compliance', icon: Shield }
];

const PRICING_MODELS = [
  { value: 'all', label: 'All Pricing' },
  { value: 'per_use', label: 'Per Use' },
  { value: 'per_month', label: 'Monthly' },
  { value: 'per_scan', label: 'Per Scan' },
  { value: 'per_analysis', label: 'Per Analysis' },
  { value: 'per_document', label: 'Per Document' },
  { value: 'per_workflow', label: 'Per Workflow' },
  { value: 'per_api', label: 'Per API' },
  { value: 'per_profile', label: 'Per Profile' },
  { value: 'per_policy', label: 'Per Policy' },
  { value: 'per_report', label: 'Per Report' },
  { value: 'per_validation', label: 'Per Validation' }
];

export const MarketplaceCatalogPage: React.FC = () => {
  const [listings, setListings] = useState<MarketplaceListing[]>([]);
  const [vendors, setVendors] = useState<{ [key: string]: Vendor }>({});
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedPricing, setSelectedPricing] = useState('all');
  const [sortBy, setSortBy] = useState('created_at');
  const [showFilters, setShowFilters] = useState(false);
  const [cart, setCart] = useState<string[]>([]);

  useEffect(() => {
    loadMarketplaceData();
  }, []);

  const loadMarketplaceData = async () => {
    try {
      const [listingsData, vendorsData] = await Promise.all([
        api('/api/v1/marketplace/listings'),
        api('/api/v1/marketplace/vendors')
      ]);

      setListings(listingsData.listings || []);
      
      const vendorMap: { [key: string]: Vendor } = {};
      vendorsData.vendors?.forEach((vendor: Vendor) => {
        vendorMap[vendor.id] = vendor;
      });
      setVendors(vendorMap);
    } catch (error) {
      console.error('Failed to load marketplace data:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredListings = listings
    .filter(listing => listing.status === 'published')
    .filter(listing => 
      selectedCategory === 'all' || listing.category === selectedCategory
    )
    .filter(listing => 
      selectedPricing === 'all' || listing.pricing_model === selectedPricing
    )
    .filter(listing => 
      searchQuery === '' || 
      listing.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      listing.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      listing.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()))
    )
    .sort((a, b) => {
      switch (sortBy) {
        case 'name':
          return a.name.localeCompare(b.name);
        case 'price':
          return a.price - b.price;
        case 'downloads':
          return b.downloads - a.downloads;
        case 'rating':
          return b.rating - a.rating;
        case 'created_at':
        default:
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      }
    });

  const addToCart = (listingId: string) => {
    setCart([...cart, listingId]);
  };

  const removeFromCart = (listingId: string) => {
    setCart(cart.filter(id => id !== listingId));
  };

  const isInCart = (listingId: string) => cart.includes(listingId);

  const formatPrice = (price: number, model: string) => {
    if (model === 'per_month') {
      return `$${price}/mo`;
    }
    return `$${price}`;
  };

  const getCategoryIcon = (category: string) => {
    const cat = CATEGORIES.find(c => c.value === category);
    return cat ? cat.icon : Package;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-sm text-gray-400">Loading marketplace...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Search and Filters */}
      <div className="flex flex-col lg:flex-row gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
          <input
            type="text"
            placeholder="Search listings..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-orange-500"
          />
        </div>
        
        <div className="flex gap-2">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white hover:bg-gray-700 transition-colors flex items-center gap-2"
          >
            <Filter size={16} />
            Filters
            <ChevronDown size={16} className={`transform transition-transform ${showFilters ? 'rotate-180' : ''}`} />
          </button>
          
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-orange-500"
          >
            <option value="created_at">Newest First</option>
            <option value="name">Name</option>
            <option value="price">Price</option>
            <option value="downloads">Most Downloaded</option>
            <option value="rating">Highest Rated</option>
          </select>
        </div>
      </div>

      {/* Filters Panel */}
      {showFilters && (
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Category</label>
              <div className="grid grid-cols-2 gap-2">
                {CATEGORIES.map(category => {
                  const Icon = category.icon;
                  return (
                    <button
                      key={category.value}
                      onClick={() => setSelectedCategory(category.value)}
                      className={`px-3 py-2 rounded-lg text-sm flex items-center gap-2 transition-colors ${
                        selectedCategory === category.value
                          ? 'bg-orange-500 text-white'
                          : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                      }`}
                    >
                      <Icon size={14} />
                      {category.label}
                    </button>
                  );
                })}
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Pricing Model</label>
              <div className="grid grid-cols-2 gap-2">
                {PRICING_MODELS.map(model => (
                  <button
                    key={model.value}
                    onClick={() => setSelectedPricing(model.value)}
                    className={`px-3 py-2 rounded-lg text-sm transition-colors ${
                      selectedPricing === model.value
                        ? 'bg-orange-500 text-white'
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    }`}
                  >
                    {model.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Results Summary */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-gray-400">
          Showing {filteredListings.length} of {listings.length} listings
        </div>
        {cart.length > 0 && (
          <div className="flex items-center gap-2 text-sm">
            <ShoppingCart size={16} className="text-orange-400" />
            <span className="text-orange-400">{cart.length} items in cart</span>
          </div>
        )}
      </div>

      {/* Listings Grid */}
      {filteredListings.length === 0 ? (
        <div className="text-center py-12">
          <Package className="mx-auto text-gray-500 mb-4" size={48} />
          <h3 className="text-lg font-semibold text-white mb-2">No listings found</h3>
          <p className="text-gray-400">Try adjusting your filters or search terms</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredListings.map(listing => {
            const vendor = vendors[listing.vendor_id];
            const CategoryIcon = getCategoryIcon(listing.category);
            const inCart = isInCart(listing.id);
            
            return (
              <div key={listing.id} className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden hover:border-orange-500 transition-colors">
                {/* Header */}
                <div className="p-4 border-b border-gray-700">
                  <div className="flex items-start justify-between mb-3">
                    <div className="w-12 h-12 bg-gray-700 rounded-lg flex items-center justify-center">
                      {listing.icon_url ? (
                        <img src={listing.icon_url} alt={listing.name} className="w-8 h-8" />
                      ) : (
                        <CategoryIcon size={20} className="text-orange-400" />
                      )}
                    </div>
                    <div className="text-right">
                      <div className="text-lg font-bold text-orange-400">
                        {formatPrice(listing.price, listing.pricing_model)}
                      </div>
                      <div className="text-xs text-gray-400">
                        {listing.pricing_model.replace('_', ' ')}
                      </div>
                    </div>
                  </div>
                  
                  <h3 className="font-semibold text-white mb-2">{listing.name}</h3>
                  <p className="text-sm text-gray-400 line-clamp-2 mb-3">{listing.description}</p>
                  
                  <div className="flex items-center justify-between text-xs text-gray-400">
                    <span>{vendor?.business_name || 'Unknown Vendor'}</span>
                    <div className="flex items-center gap-1">
                      <Star size={12} className="text-yellow-400" />
                      {listing.rating.toFixed(1)}
                    </div>
                  </div>
                </div>
                
                {/* Tags */}
                <div className="px-4 py-2 border-b border-gray-700">
                  <div className="flex flex-wrap gap-1">
                    {listing.tags.slice(0, 3).map((tag, index) => (
                      <span key={index} className="px-2 py-1 bg-gray-700 text-xs text-gray-300 rounded">
                        {tag}
                      </span>
                    ))}
                    {listing.tags.length > 3 && (
                      <span className="px-2 py-1 bg-gray-700 text-xs text-gray-300 rounded">
                        +{listing.tags.length - 3}
                      </span>
                    )}
                  </div>
                </div>
                
                {/* Stats */}
                <div className="px-4 py-2 border-b border-gray-700">
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-1 text-gray-400">
                      <Download size={12} />
                      {listing.downloads.toLocaleString()} downloads
                    </div>
                    <div className="flex items-center gap-1 text-gray-400">
                      <ExternalLink size={12} />
                      {listing.category}
                    </div>
                  </div>
                </div>
                
                {/* Actions */}
                <div className="p-4">
                  <div className="flex gap-2">
                    <button
                      onClick={() => inCart ? removeFromCart(listing.id) : addToCart(listing.id)}
                      className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2 ${
                        inCart
                          ? 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                          : 'bg-orange-500 text-white hover:bg-orange-600'
                      }`}
                    >
                      <ShoppingCart size={14} />
                      {inCart ? 'Remove from Cart' : 'Add to Cart'}
                    </button>
                    <button className="px-3 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors">
                      <ExternalLink size={14} />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
