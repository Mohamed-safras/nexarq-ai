import { Nav }       from '@/components/nav'
import { Hero }      from '@/components/sections/hero'
import { Approach }  from '@/components/sections/approach'
import { Analytics } from '@/components/sections/analytics'
import { Install }   from '@/components/sections/install'
import { Footer }    from '@/components/sections/footer'

export default function HomePage() {
  return (
    <>
      <Nav />
      <main>
        <Hero />
        <Approach />
        <Analytics />
        <Install />
      </main>
      <Footer />
    </>
  )
}
