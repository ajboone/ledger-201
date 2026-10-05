import logo from "../assets/logo.png";
import { Link } from "react-router-dom";
import { typography } from "../typography";
import {
  logoStyles,
  navItemsContainerStyles,
  navLinkStyles,
  navStyles,
} from "./styles";
export const Navbar = () => {
  const navItems = [
    { label: "Chatbot", href: "/" },
    { label: "Vendor", href: "/vendor" },
    { label: "Locations", href: "/location" },
    { label: "Daily Review (Demo)", href: "/daily-review" },
    { label: "Square Reports", href: "/square-reports" },
  ];

  return (
    <nav style={navStyles}>
      <Link to="/" style={logoStyles}>
        <img src={logo} alt="Ledger 201" width="200em" />
        <h1 style={typography.h1}>Ledger 201</h1>
      </Link>
      <ul style={navItemsContainerStyles}>
        {navItems.map((item) => (
          <li key={item.label}>
            <Link style={navLinkStyles} to={item.href}>
              {item.label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
};

export default Navbar;
