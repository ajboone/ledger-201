import "./App.css";
import Chatbot from "./Chatbot";
import Sidebar from "./Sidebar";

const App = () => {
  return (
    <div className="app">
      <Sidebar />
      <Chatbot />
    </div>
  );
};

export default App;
