
import { Link, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { FileText, Upload, Layout, Zap, Home } from "lucide-react";

const Navigation = () => {
  const location = useLocation();

  const navItems = [
    { path: "/", label: "Dashboard", icon: Home },
    { path: "/upload", label: "Upload", icon: Upload },
    { path: "/templates", label: "Templates", icon: Layout },
    { path: "/analyze", label: "Analyze", icon: Zap },
  ];

  return (
    <nav className="bg-white shadow-sm border-b">
      <div className="container mx-auto px-6">
        <div className="flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-2 font-bold text-xl text-gray-900">
            <FileText className="w-6 h-6 text-blue-600" />
            ProposalGen AI
          </Link>
          
          <div className="flex items-center gap-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;
              
              return (
                <Link key={item.path} to={item.path}>
                  <Button 
                    variant={isActive ? "default" : "ghost"} 
                    className="flex items-center gap-2"
                  >
                    <Icon className="w-4 h-4" />
                    {item.label}
                  </Button>
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navigation;
