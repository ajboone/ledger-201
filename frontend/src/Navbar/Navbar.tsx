export const Navbar = () => {
  const navItems = ["Main", "Vendor"];

  return (
    <nav>
      <ul>
        {navItems.map((item) => (
          <li key={item}>
            <a href={`/${item.toLowerCase()}`}>{item}</a>
          </li>
        ))}
      </ul>
    </nav>
  );
};

export default Navbar;
