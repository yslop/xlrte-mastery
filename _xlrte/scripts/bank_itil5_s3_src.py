"""XLRTE Schattenprüfung S3 — 40 ungesehene, selbst formulierte Fragen im PeopleCert-Formprofil.
Blueprint: Kat 1 (12), Kat 2 (4), Kat 3 (4), Kat 4 (16), Kat 5 (2), Kat 6 (1), Kat 7 (1). Bloom: 24 BL2 (60 %), 16 BL1 (40 %).
Schwerpunkt: Fehlerbilder aus SP1 (1.1.3, 1.2.4, 2.2.2, 4.2.4, 4.4.2, 4.5.4) und bisher selten abgefragte Lernziele.
Keine Texte aus Buch oder Musterprüfungen; Sachaussagen stammen aus Syllabus/Glossar der Projektdaten.
Format: (lo, bl, q, [key, d1, d2, d3], why) – Schlüssel steht im Source-Array immer an Index 0 und wird beim Kompilieren
deterministisch auf je 10 × A/B/C/D verteilt.
Kompilieren: python3 scripts/bank_itil5_s3_src.py  →  data/items_itil5_s3.json
"""
import json, os, random

Q = [
    # ---- Kategorie 1 (12): 5 BL1, 7 BL2 -------------------------------------------------------------------
    ("1.1.3", 2,
     "Ein Energieversorger bietet Haushalten eine App zur Verbrauchsübersicht an und verspricht, dass Kunden damit ihre Stromkosten besser steuern können. Der Projektleiter erklärt dem Vorstand, wie sich App und Angebot zueinander verhalten. Welche Aussage ist ZUTREFFEND?",
     ["Der digitale Service beruht auf dem digitalen Produkt: Das Produkt stellt die Fähigkeiten bereit, das Serviceangebot beschreibt den potenziellen Wert für die Kunden",
      "Das digitale Produkt beruht auf dem digitalen Service: Der Service liefert die Fähigkeiten, das Produkt beschreibt den potenziellen Wert für die Kunden",
      "Produkt und Service sind voneinander unabhängig, weil das Produkt technisch und der Service rein kommerziell definiert ist",
      "Das digitale Produkt besteht ausschließlich aus Serviceaktionen, die Mitarbeitende des Energieversorgers für Kunden erbringen"],
     "Digitale Services basieren immer auf digitalen Produkten (nicht umgekehrt). Produkte stellen Fähigkeiten bereit, Serviceangebote beschreiben den potenziellen Wert. Beide hängen voneinander ab; Serviceaktionen sind ein eigenes Konzept."),

    ("1.1.4", 1,
     "In einer Schulung soll definiert werden, was Continual Improvement im ITIL-Sinne ausmacht. Welche Beschreibung ist KORREKT?",
     ["Eine wiederkehrende organisatorische Tätigkeit auf allen Ebenen, damit die Organisation die Erwartungen der Stakeholder fortlaufend erfüllt",
      "Ein einmaliges Verbesserungsprojekt der Geschäftsleitung, das nach der Umsetzung der Maßnahmen formal abgeschlossen wird",
      "Eine Methode, die ausschließlich die Kosten eines Services senkt, ohne dessen Funktionalität oder Qualität zu verändern",
      "Ein jährlicher Auditzyklus, in dem die Geschäftsführung die Einhaltung der Compliance-Vorgaben bewertet"],
     "Continual Improvement ist wiederkehrend und findet auf allen Ebenen statt. Es ist weder einmalig noch auf Kosten oder Audits beschränkt."),

    ("1.1.6", 1,
     "Ein Hersteller liefert einem Unternehmen 200 Laptops und überträgt dabei das Eigentum samt Rechten und Pflichten. Welches ITIL-Konzept beschreibt diese Laptops?",
     ["Waren",
      "Serviceaktionen",
      "Zugang zu Ressourcen",
      "Serviceangebot"],
     "Waren sind materielle Ressourcen, die zusammen mit dem Eigentum und den damit verbundenen Rechten und Pflichten übertragen werden. Serviceaktionen sind Handlungen, Zugang zu Ressourcen ist Nutzung ohne Eigentumsübergang, ein Serviceangebot ist eine Beschreibung."),

    ("1.2.4", 2,
     "Ein Rechenzentrumsbetreiber stellt einem Kunden Rechenleistung zur Verfügung, die der Kunde im Rahmen vereinbarter Bedingungen selbst nutzt, ohne dass Eigentum an der Hardware übergeht. Welches Konzept liegt vor?",
     ["Zugang zu Ressourcen",
      "Warentransfer",
      "Serviceaktion",
      "Nachhaltigkeit"],
     "Beim Zugang zu Ressourcen nutzt der Servicekonsument Ressourcen des Providers gemäß vereinbarter Bedingungen. Beim Warentransfer wechselt das Eigentum, eine Serviceaktion ist eine Handlung des Providers."),

    ("1.2.4", 2,
     "Ein Mitarbeiter des Service Providers richtet für eine Kundin nach Absprache ein neues E-Mail-Postfach ein und schult sie kurz. Welcher Bestandteil des Services wird hier konkret erbracht?",
     ["Eine Serviceaktion",
      "Ein Warentransfer",
      "Ein Zugang zu Ressourcen",
      "Ein Serviceangebot"],
     "Eine Handlung, die vom Provider (allein oder gemeinsam mit dem Konsumenten) durchgeführt wird, ist eine Serviceaktion. Die Erfüllung eines Service Requests ist eine typische Serviceaktion."),

    ("1.3.2", 1,
     "Ein Controller sagt: „Wir müssen berücksichtigen, dass bei der Migration ein Datenverlust auftreten und dadurch Schaden entstehen könnte.“ Welcher Begriff wird damit beschrieben?",
     ["Risiko",
      "Kosten",
      "Output",
      "Service Level"],
     "Ein Risiko ist ein mögliches Event, das zu Schaden oder Verlust führen oder das Erreichen von Zielen erschweren könnte. Kosten sind der ausgegebene Geldbetrag."),

    ("1.3.5", 2,
     "Ein Logistikunternehmen nutzt eine Routenplanungsplattform eines Providers. Die Disponenten pflegen dort ihre Aufträge und Fahrzeugdaten ein, der Provider betreibt und verbessert die Plattform. Was beschreibt das Beispiel AM BESTEN?",
     ["Gemeinsame Wertschöpfung: Provider und Konsument bringen jeweils Ressourcen und Handlungen ein, und der Wert entsteht in der Nutzung",
      "Wertlieferung durch den Provider: Der Wert wird vollständig vom Provider erzeugt und vom Konsumenten lediglich abgenommen",
      "Warentransfer: Mit der Nutzung der Plattform geht das Eigentum an der Software auf das Logistikunternehmen über",
      "Outputerzeugung: Der Konsument erzielt ausschließlich dadurch Wert, dass der Provider die vereinbarten Outputs liefert"],
     "Wert entsteht gemeinsam: Der Provider stellt Produkte und Services bereit, der Konsument bringt eigene Ressourcen und Handlungen ein und nutzt sie. Wert wird nicht einseitig geliefert."),

    ("1.3.6", 2,
     "Ein Kunde bewertet einen neuen Service. Der Nutzen ist hoch, aber die Kosten sind so hoch und die Risiken so groß, dass der Konsument den Service als nicht lohnend einstuft. Was erklärt das AM BESTEN?",
     ["Wert wird aus dem Zusammenspiel von Ergebnissen, Kosten und Risiken wahrgenommen; positive Ergebnisse allein genügen nicht",
      "Wert entsteht ausschließlich durch die Anzahl der gelieferten Outputs, unabhängig von Kosten und Risiken des Konsumenten",
      "Kosten und Risiken betreffen nur den Provider, deshalb bleibt die Wertwahrnehmung des Konsumenten davon unberührt",
      "Ein Service ist wertvoll, sobald er die vereinbarte Utility erfüllt, auch wenn die Nutzung dem Konsumenten schadet"],
     "Gemeinsame Wertschöpfung hängt davon ab, wie stark positive Ergebnisse die negativen Effekte (Kosten, Risiken) überwiegen. Kosten und Risiken betreffen auch den Konsumenten."),

    ("1.4.3", 1,
     "Welche Beschreibung der Service Journey ist KORREKT?",
     ["Die Summe der Aktivitäten und Interaktionen, die Organisationen in Servicebeziehungen durchführen, um ihre Rollen als Provider und Konsument zu erfüllen",
      "Der Weg eines einzelnen Incidents vom Anruf des Anwenders bis zur Wiederherstellung des Services im Support",
      "Die zeitliche Abfolge der Lebenszyklusaktivitäten, die für jeden Service in genau derselben Reihenfolge durchlaufen werden",
      "Die Dokumentation sämtlicher Vertragsbestandteile einer Servicebeziehung von der Ausschreibung bis zur Kündigung"],
     "Die Service Journey umfasst Aktivitäten und Interaktionen in Servicebeziehungen, mit denen Provider und Konsument ihre Rollen erfüllen. Sie ist weder ein Incident-Ablauf noch eine starre Reihenfolge."),

    ("1.4.5", 1,
     "Ein Service Provider vereinbart mit einem Kunden Messgrößen, die festlegen, welche Qualität erwartet bzw. erreicht wird, zum Beispiel Verfügbarkeit und Reaktionszeit. Wie heißt dieses Konzept?",
     ["Service Level",
      "Servicequalität",
      "Serviceangebot",
      "Service Journey"],
     "Ein Service Level ist eine Reihe von Messgrößen, die die erwartete oder erreichte Servicequalität definieren. Servicequalität ist die Summe der Merkmale, die für die Bedürfniserfüllung relevant sind."),

    ("1.4.8", 2,
     "In einem Workshop wird diskutiert, welche Rolle ein Servicekonsument in einer Servicebeziehung hat. Welche Aussage ist ZUTREFFEND?",
     ["Er trägt aktiv zur gemeinsamen Wertschöpfung bei, indem er eigene Ressourcen, Fähigkeiten und Handlungen einbringt",
      "Er ist ausschließlich passiver Empfänger und hat auf das Ergebnis des Services keinen Einfluss",
      "Er übernimmt die Verantwortung für Betrieb und Weiterentwicklung der digitalen Produkte des Providers",
      "Er besteht stets aus einer einzelnen Person, die den Service nutzt und zugleich bezahlt"],
     "Konsumenten sind aktive Mitgestalter. Sponsor, Kunde und Anwender sind Rollen auf Konsumentenseite; sie können von verschiedenen Personen wahrgenommen werden."),

    ("1.4.11", 2,
     "Ein Hochschulverbund wählt zwischen zwei Providern. Provider X ist funktional etwas schwächer, verpflichtet sich aber vertraglich zu einem klimaneutralen Betrieb der Rechenzentren. Welcher Aspekt der Servicequalität wird damit PRIMÄR adressiert?",
     ["Nachhaltigkeit",
      "Utility",
      "Warranty",
      "User Experience"],
     "Nachhaltigkeit betrifft die ökologischen und sozialen Auswirkungen eines Services. Utility ist die Funktionalität, Warranty die Zusicherung der Anforderungen (Verfügbarkeit, Sicherheit), User Experience die Interaktion der Anwender."),

    # ---- Kategorie 2 (4): 1 BL1, 3 BL2 ---------------------------------------------------------------------
    ("2.1.1", 1,
     "Welche Aufzählung enthält die vier Dimensionen des Produkt- und Servicemanagements vollständig und korrekt?",
     ["Organisationen und Menschen; Partner und Lieferanten; Informationen und Technologie; Wertströme und Prozesse",
      "Organisationen und Menschen; Partner und Lieferanten; Kosten und Risiken; Wertströme und Prozesse",
      "Strategie und Governance; Partner und Lieferanten; Informationen und Technologie; Wertströme und Prozesse",
      "Organisationen und Menschen; Kunden und Lieferanten; Informationen und Technologie; Practices und Prozesse"],
     "Die vier Dimensionen sind Organisationen und Menschen, Partner und Lieferanten, Informationen und Technologie sowie Wertströme und Prozesse."),

    ("2.1.2", 2,
     "Ein Team prüft, ob es für einen neuen Service alle nötigen Verträge mit Drittanbietern und die Abhängigkeit von einem externen Cloud-Provider berücksichtigt hat. Welche Dimension wird damit betrachtet?",
     ["Partner und Lieferanten",
      "Organisationen und Menschen",
      "Informationen und Technologie",
      "Wertströme und Prozesse"],
     "Partner und Lieferanten umfasst die Beziehungen zu anderen Organisationen, die an Design, Entwicklung, Bereitstellung oder Support beteiligt sind, einschließlich Verträgen und Vereinbarungen."),

    ("2.1.3", 2,
     "Ein Unternehmen führt ein neues Ticketsystem ein, bearbeitet aber weder Rollen und Schulungen noch bestehende Abläufe oder Lieferantenverträge. Was ist die wahrscheinlichste Lehre im Sinne der vier Dimensionen?",
     ["Es fehlt der ganzheitliche Ansatz: Alle vier Dimensionen müssen ausgewogen berücksichtigt werden, sonst wird der Wert nicht erreicht",
      "Die Dimension Informationen und Technologie ist die wichtigste und genügt, solange die Software sorgfältig ausgewählt wurde",
      "Die vier Dimensionen gelten nur für die Aktivität Build und sind in Betrieb und Support nicht mehr relevant",
      "Die Dimensionen sollten nacheinander abgearbeitet werden, wobei jede erst nach Abschluss der vorherigen beginnt"],
     "Die vier Dimensionen sind gleichermaßen zu berücksichtigen. Vernachlässigt man eine, entsteht ein Ungleichgewicht, das die Wertschöpfung gefährdet."),

    ("2.2.2", 2,
     "Ein Team stellt fest, dass unklar ist, wer bei Störungen entscheiden darf und wie Eskalationen kommuniziert werden. Welche Dimension ist in erster Linie betroffen?",
     ["Organisationen und Menschen",
      "Wertströme und Prozesse",
      "Partner und Lieferanten",
      "Informationen und Technologie"],
     "Organisationen und Menschen stellt sicher, dass Rollen, Verantwortlichkeiten sowie Systeme von Autorität und Kommunikation klar definiert sind. Wertströme und Prozesse beschreibt die Workflows und Aktivitäten."),

    # ---- Kategorie 3 (4): 3 BL1, 1 BL2 ---------------------------------------------------------------------
    ("3.1.2", 2,
     "Ein Berater erklärt, wie Lebenszyklus und Wertschöpfungskette zusammenhängen. Welche Aussage ist ZUTREFFEND?",
     ["Die Aktivitäten der Wertschöpfungskette ermöglichen das Management digitaler Produkte und Services über ihren Lebenszyklus, unterstützt durch Management-Practices",
      "Der Lebenszyklus besteht aus den Practices, während die Wertschöpfungskette ausschließlich den Betrieb eines Services abdeckt",
      "Die Wertschöpfungskette beginnt erst, nachdem der Lebenszyklus eines Produkts vollständig abgeschlossen wurde",
      "Lebenszyklus und Wertschöpfungskette sind zwei getrennte Modelle ohne jegliche Verbindung zueinander"],
     "Aktivitäten der Wertschöpfungskette werden von Organisationen durchgeführt, um Produkte und Services über ihren Lebenszyklus zu managen. Jede Aktivität wird durch mehrere Practices unterstützt."),

    ("3.2.2", 1,
     "In welcher Lebenszyklusaktivität werden Prototypen und Spezifikationen erstellt, die Funktionalität, User Experience und den operativen Rahmen beschreiben?",
     ["Design",
      "Build",
      "Transition",
      "Discover"],
     "Design erzeugt Prototypen und Spezifikationen. Build entwickelt, integriert und testet; Transition überführt Änderungen in den Betrieb; Discover erkundet Bedürfnisse und Möglichkeiten."),

    ("3.2.4", 1,
     "Welche Lebenszyklusaktivität sorgt dafür, dass aus Designs funktionsfähige digitale Produkte entwickelt, integriert und getestet werden?",
     ["Build",
      "Design",
      "Operate",
      "Acquire"],
     "Build entwickelt, integriert und testet digitale Produkte. Design beschreibt sie, Operate erhält und überwacht sie, Acquire beschafft Bestandteile."),

    ("3.2.6", 1,
     "Was ist der Zweck der Lebenszyklusaktivität „Operate“?",
     ["Digitale Produkte und unterstützende Systeme erhalten und überwachen, um optimale Leistung und Zuverlässigkeit sicherzustellen",
      "Prototypen und Spezifikationen erstellen, die Funktionalität und User Experience der Produkte beschreiben",
      "Anwender und Kunden bei Fragen unterstützen und Störungen im direkten Kontakt zügig beheben",
      "Neue Bedürfnisse der Stakeholder erkunden und daraus mögliche Produkte und Services ableiten"],
     "Operate erhält und überwacht Produkte und Systeme für Leistung und Zuverlässigkeit. Design = Prototypen/Spezifikationen, Support = Unterstützung der Anwender, Discover = Erkunden."),

    # ---- Kategorie 4 (16): 7 BL1, 9 BL2 --------------------------------------------------------------------
    ("4.2.4", 2,
     "Ein Team arbeitet in kurzen Iterationen und holt nach jeder Iteration Feedback der Anwender ein. Welchen HAUPTZWECK erfüllt dieses Vorgehen?",
     ["Sicherstellen, dass die Verbesserungen unter sich ändernden Umständen relevant und wirksam bleiben",
      "Erreichen, dass sich alle Stakeholder in jeder Frage einig sind, bevor die nächste Iteration beginnt",
      "Den Bedarf an späteren Korrekturen ausschließen, sobald die Arbeit einmal begonnen wurde",
      "Die Prioritäten während der Umsetzung einfrieren, damit der ursprüngliche Plan unverändert bleibt"],
     "Iterative Weiterentwicklung mit Feedback ermöglicht schnellere Reaktion auf Bedürfnisse und früheres Erkennen von Fehlern. Feedback steuert nach; es verhindert weder Anpassung noch erzwingt es Einigkeit."),

    ("4.2.4", 2,
     "Ein Entwicklungsteam liefert alle sechs Monate ein großes Release, Rückmeldungen kommen erst danach. Welche Änderung entspricht dem Grundprinzip „Iterative Weiterentwicklung mit Feedback“ AM BESTEN?",
     ["In kleinen, zeitlich begrenzten Schritten arbeiten und Feedbackschleifen in den Workflow einbetten, um früher zu lernen",
      "Den Planungsaufwand weiter erhöhen, damit das halbjährliche Release möglichst fehlerfrei und unveränderlich bleibt",
      "Das Feedback der Anwender erst sammeln, wenn das Release abgeschlossen und freigegeben wurde",
      "Auf Feedback verzichten und stattdessen die Tests am Ende des Zyklus verlängern"],
     "Zeitlich begrenzte, iterative Arbeit mit eingebetteten Feedbackschleifen erlaubt schnellere Reaktionen, früheres Erkennen von Fehlern und höhere Qualität."),

    ("4.1.2", 2,
     "Die Geschäftsführung fragt, wozu das ITIL Value System dient. Welche Antwort trifft den Zweck AM BESTEN?",
     ["Es stellt sicher, dass die Organisation gemeinsam mit allen Stakeholdern durch Nutzung und Management von Produkten und Services fortlaufend Wert schafft",
      "Es legt für jeden Service verbindlich fest, welche Kennzahlen mit welchem Zielwert im Jahresbericht zu veröffentlichen sind",
      "Es ersetzt die Governance der Organisation und gibt vor, welche Entscheidungen das Management zu treffen hat",
      "Es beschreibt ausschließlich die Aktivitäten des IT-Betriebs und ist für Entwicklung und Strategie nicht vorgesehen"],
     "Das ITIL Value System zeigt, wie alle Komponenten und Aktivitäten einer Organisation zusammenwirken, um Wertschöpfung mit digitalen Produkten und Services zu ermöglichen."),

    ("4.2.9", 2,
     "Ein Manager möchte aus den ITIL-Grundprinzipien nur das Prinzip „Auf Einfachheit achten“ umsetzen, weil es am bequemsten erscheint. Welche Antwort entspricht der Wechselwirkung der Grundprinzipien?",
     ["Die Prinzipien sind voneinander abhängig und sollen gemeinsam angewendet werden, zum Beispiel braucht Iteration das Feedback aus der Zusammenarbeit",
      "Ein Prinzip ist immer vorherrschend, und die anderen sind nur anzuwenden, wenn das vorherrschende Prinzip es zulässt",
      "Die Prinzipien sind unabhängig, und jede Organisation darf frei wählen, welches einzelne Prinzip sie umsetzt",
      "Die Prinzipien werden strikt nacheinander in der Reihenfolge ihrer Aufzählung angewendet"],
     "Die Prinzipien interagieren und hängen voneinander ab. Sie sind in Kombination anzuwenden, nicht einzeln oder in fester Reihenfolge."),

    ("4.3.1", 1,
     "Welche Definition von Governance ist KORREKT?",
     ["Das System, mit dem eine Organisation geführt und gesteuert wird",
      "Eine Sammlung von Messgrößen, die für Verbesserungszwecke überwacht oder gemeldet werden",
      "Eine Reihe organisatorischer Ressourcen für die Ausführung bestimmter Arbeit",
      "Ein Modell, das beschreibt, wie die Organisation mit Kunden Wert schafft"],
     "Governance ist das System, mit dem eine Organisation geführt und gesteuert wird. Die anderen Optionen beschreiben Messgrößen, Practices bzw. das Betriebsmodell."),

    ("4.3.2", 2,
     "Ein Vorstand soll die Governance digitaler Technologie wahrnehmen. Welche Aktivitäten gehören dazu?",
     ["Bewerten, Führen und Überwachen sowie das Einbinden der Stakeholder",
      "Entwickeln, Testen und Bereitstellen der digitalen Produkte in eigener Verantwortung",
      "Beschaffen, Betreiben und Entsorgen von Technologie nach festen Jahresplänen",
      "Messen, Berichten und Archivieren aller Betriebsdaten für spätere Audits"],
     "Governance ist befähigend: Sie bewertet, gibt Richtung vor (Führen), überwacht und bindet Stakeholder ein. Sie ist keine reine Kontrolle."),

    ("4.4.2", 1,
     "Ein Team beschreibt in einem Dokument die kritischen Aspekte, Anforderungen und Eigenschaften eines geplanten Produkts. Wie heißt dieses Dokument?",
     ["Produktspezifikation",
      "Produktprototyp",
      "Release",
      "Known Error"],
     "Eine Produktspezifikation beschreibt kritische Aspekte, Anforderungen und Eigenschaften. Ein Prototyp ist eine erste testbare Version zur Validierung des Designs."),

    ("4.4.2", 1,
     "Ein Team baut eine einfache, klickbare Vorversion einer Anwendung, um mit Nutzern zu prüfen, ob das Design funktioniert. Was liegt hier vor?",
     ["Ein Produktprototyp",
      "Eine Produktspezifikation",
      "Ein Continuous Deployment",
      "Ein Service Level Agreement"],
     "Ein Prototyp ist die initiale Version zum Testen eines Designs und dient der Validierung von Annahmen. Die Spezifikation beschreibt dagegen Anforderungen und Eigenschaften."),

    ("4.4.6", 1,
     "Ein Betriebsteam analysiert Metriken, Logs und Traces, um den inneren Zustand eines komplexen Systems zu verstehen. Welches Konzept wird angewendet?",
     ["Observability",
      "Continuous Integration",
      "Wertstromabbildung",
      "Warranty"],
     "Observability ist die Fähigkeit, den internen Zustand eines Systems über seine externen Outputs (Metriken, Logs, Traces) zu verstehen."),

    ("4.4.8", 1,
     "Eine Ursache für wiederkehrende Incidents wurde analysiert, aber noch nicht beseitigt. Wie nennt ITIL das?",
     ["Known Error",
      "Problem",
      "Katastrophe",
      "Event"],
     "Ein Known Error ist ein Problem, das analysiert, aber nicht gelöst wurde. Ein Problem ist die Ursache oder mögliche Ursache für Incidents, ein Fehler ist ein Mangel."),

    ("4.4.11", 2,
     "Welche Erfolgsmessgröße passt AM BESTEN zur Lebenszyklusaktivität „Support“?",
     ["Die Schnelligkeit, mit der der normale Service nach einer Störung wiederhergestellt wird",
      "Die Zahl der entdeckten neuen Bedürfnisse und Chancen im Markt pro Quartal",
      "Der Anteil der Designs, die bis zum Abschluss der Spezifikation ohne Änderungen blieben",
      "Die Höhe der Einsparungen beim Einkauf externer Komponenten im laufenden Geschäftsjahr"],
     "Support wird an der Geschwindigkeit der Wiederherstellung des normalen Services gemessen. Die anderen Messgrößen passen zu Discover, Design und Acquire."),

    ("4.4.12", 2,
     "Wie wird der Zweck einer Organisation im ITIL Value System praktisch umgesetzt?",
     ["Über das Betriebsmodell, das durch die Aktivitäten der Wertschöpfungskette und die Management-Practices unterstützt wird",
      "Über die Governance, die den Zweck unmittelbar in einzelne Incidents und Service Requests übersetzt",
      "Über die Lebenszyklusaktivität Discover, die alleine den Zweck in ausführbare Prozesse überführt",
      "Über die Grundprinzipien, die als Betriebsmodell der Organisation verbindlich vorgegeben werden"],
     "Zweck → Betriebsmodell → unterstützt durch Wertschöpfungskette und Practices. Das Betriebsmodell zeigt, wie die Organisation betrieben wird und mit Kunden Wert schafft."),

    ("4.5.4", 2,
     "Eine Teamleiterin möchte wissen, welche Rollen, Kompetenzen und Verantwortlichkeiten für eine Practice benötigt werden. Wo im offiziellen Practice-Leitfaden findet sie das?",
     ["Im Aspekt „Organisationen und Menschen“",
      "Im Aspekt „Allgemeine Informationen“",
      "Im Aspekt „Partner und Lieferanten“",
      "Im Aspekt „Assessment und Entwicklung von Fähigkeiten“"],
     "Organisationen und Menschen beschreibt Rollen, Kompetenzen und Verantwortlichkeiten. Die anderen Aspekte behandeln Zweck/Kennzahlen, Drittparteien bzw. Reifegrade."),

    ("4.5.6", 1,
     "Ein Programmleiter nennt „ausreichend geschulte Mitarbeitende“ als notwendige Voraussetzung dafür, dass ein angestrebtes Resultat erreicht wird. Welcher Begriff wird damit beschrieben?",
     ["Kritischer Erfolgsfaktor (CSF)",
      "Messgröße",
      "Service Level",
      "Output"],
     "Ein Kritischer Erfolgsfaktor ist eine notwendige Voraussetzung für das Erreichen angestrebter Resultate. Eine Messgröße ist eine Messung oder Berechnung zur Überwachung."),

    ("4.6.1", 1,
     "Welche Frage steht im ITIL Continual Improvement Model am ANFANG?",
     ["Was ist unsere Vision?",
      "Wo stehen wir jetzt?",
      "Wo wollen wir hin?",
      "Kommen wir voran?"],
     "Reihenfolge: Vision → Wo stehen wir jetzt → Wo wollen wir hin → Wie kommen wir dorthin → Maßnahmen ergreifen → Kommen wir voran → Wie stellen wir sicher, dass Verbesserungen relevant bleiben."),

    ("4.6.3", 2,
     "Welche Aussage über Continual Improvement im ITIL Value System ist KORREKT?",
     ["Es gilt für das gesamte Value System, also Produkte, Services, Practices und Beziehungen, und findet auf allen Ebenen statt",
      "Es ist eine Practice der IT-Abteilung und betrifft ausschließlich Services, die bereits im Betrieb sind",
      "Es beginnt erst nach Abschluss der Lebenszyklusaktivität Transition und endet mit der Außerbetriebnahme",
      "Es wird ausschließlich vom Management angestoßen, während Teams und Anwender nur Aufträge ausführen"],
     "Continual Improvement ist Komponente des Value Systems, Practice und Modell zugleich und findet auf allen Ebenen statt."),

    # ---- Kategorie 5 (2): 2 BL2 ----------------------------------------------------------------------------
    ("5.2.1", 2,
     "Ein Team behandelt eine stabile Routineaufgabe und ein ungeklärtes, neuartiges Problem mit demselben starren Vorgehen. Welche Erkenntnis des Komplexitätsdenkens wird dabei missachtet?",
     ["Arbeitskontexte sind unterschiedlich komplex und erfordern jeweils angemessen unterschiedliche Reaktionen",
      "Komplexität lässt sich durch ausführliche Dokumentation vollständig beseitigen, sodass ein einheitliches Vorgehen genügt",
      "Nur neuartige Probleme sind komplex, und für sie gilt grundsätzlich dasselbe Vorgehen wie für Routineaufgaben",
      "Komplexe Workflows sollten stets sofort automatisiert werden, bevor ihr Kontext verstanden wurde"],
     "Komplexitätsdenken erkennt verschiedene Komplexitätsebenen. Workflows sind kontextgerecht zu optimieren, nicht einheitlich zu behandeln."),

    ("5.3.3", 2,
     "Eine Wertstromabbildung zeigt, dass ein Antrag insgesamt 6 Tage unterwegs ist, davon 4 Stunden aktiver Bearbeitung und der Rest als Liegezeit in Warteschlangen. Wo liegt das größte Verbesserungspotenzial?",
     ["In der Wartezeit zwischen den Arbeitsschritten",
      "In der reinen Zykluszeit der aktiven Bearbeitung",
      "In der Anzahl der abgebildeten Wertströme",
      "In der Erweiterung der Abbildung um zusätzliche Kennzahlen"],
     "Zykluszeit ist die Zeit tatsächlicher Bearbeitung, Wartezeit die Liegezeit zwischen Arbeitsschritten. Hier dominiert die Wartezeit."),

    # ---- Kategorie 6 (1): 1 BL2 ----------------------------------------------------------------------------
    ("6.2.2", 2,
     "Das ITIL KI-Fähigkeitsmodell (6C) wird in einer Schulung vorgestellt. Welcher der folgenden Begriffe gehört NICHT zu den sechs Fähigkeiten?",
     ["Containment",
      "Curation",
      "Cognition",
      "Coordination"],
     "Die 6C sind Creation, Curation, Clarification, Cognition, Communication und Coordination. Containment gehört nicht dazu."),

    # ---- Kategorie 7 (1): 1 BL2 ----------------------------------------------------------------------------
    ("7.1.2", 2,
     "Ein Unternehmen setzt DevOps-Praktiken für schnelle, kontinuierliche Bereitstellung ein und möchte zugleich das Management über den gesamten Lebenszyklus sicherstellen. Wie ergänzen sich ITIL und DevOps AM BESTEN?",
     ["ITIL liefert ein umfassendes Rahmenwerk für das Management digitaler Produkte und Services, DevOps liefert praktische Techniken für schnelle Bereitstellung",
      "DevOps ersetzt das ITIL Value System, sodass Governance und Practices nicht mehr nötig sind",
      "ITIL ist auf Entwicklung beschränkt, und DevOps deckt ausschließlich den Betrieb und den Support ab",
      "Beide Ansätze dürfen nur getrennt voneinander eingesetzt werden, damit sich ihre Begriffe nicht vermischen"],
     "ITIL und DevOps ergänzen sich: ITIL als Rahmenwerk über den Lebenszyklus, DevOps als praktische Techniken (z. B. Continuous Delivery) für widerstandsfähige, kundenorientierte Ergebnisse."),
]


def compile_items():
    rnd = random.Random(2026100203)
    pos = [0, 1, 2, 3] * 10
    rnd.shuffle(pos)
    items = []
    for n, ((lo, bl, q, opts, why), k) in enumerate(zip(Q, pos), 1):
        key, ds = opts[0], opts[1:]
        rnd.shuffle(ds)
        ordered = ds[:k] + [key] + ds[k:]
        items.append({"id": f"i5s3_{n:03d}", "exam": "itil5", "lo": lo, "bl": bl, "type": "std", "q": q, "options": ordered,
                      "answer": k, "why": why, "src": "xlrte-s3:sp-profil", "status": "shadow", "set": "S3"})
    return items


if __name__ == "__main__":
    items = compile_items()
    out = os.path.join(os.path.dirname(__file__), "..", "data", "items_itil5_s3.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
    print(len(items), "Fragen →", os.path.normpath(out))
