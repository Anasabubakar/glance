import Nav from "../components/Nav";
import Hero from "../components/Hero";
import BentoGrid from "../components/BentoGrid";
import TrustLayer from "../components/TrustLayer";
import BrainSpecs from "../components/BrainSpecs";
import Footer from "../components/Footer";

export default function Home() {
  return (
    <main className="bg-zinc-950 min-h-screen text-white selection:bg-blue-500 selection:text-white">
      <Nav />
      <Hero />
      <BentoGrid />
      <TrustLayer />
      <BrainSpecs />
      <Footer />
    </main>
  );
}
