import logo from "../assets/logo.png";
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
  ];

  return (
    <nav style={navStyles}>
      <a href="/" style={logoStyles}>
        <img src={logo} alt="Ledger 201" width="200em" />
        <h1 style={typography.h1}>Ledger 201</h1>
      </a>
      <ul style={navItemsContainerStyles}>
        {navItems.map((item) => (
          <li key={item.label}>
            <a style={navLinkStyles} href={item.href}>
              {item.label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
};

export default Navbar;
