import Nav from "@/components/landing/Nav";
import Hero from "@/components/landing/Hero";
import ProductPreview from "@/components/landing/ProductPreview";
import FeaturesBento from "@/components/landing/FeaturesBento";
import Providers from "@/components/landing/Providers";
import HowItWorks from "@/components/landing/HowItWorks";
import DownloadCTA from "@/components/landing/DownloadCTA";
import Footer from "@/components/landing/Footer";

export default function Home() {
  return (
    <main id="main-content" className="bg-bg-deep min-h-screen text-text-primary">
      <Nav />
      <Hero />
      <ProductPreview />
      <FeaturesBento />
      <Providers />
      <HowItWorks />
      <DownloadCTA />
      <Footer />
    </main>
  );
}
