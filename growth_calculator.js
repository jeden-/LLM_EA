// Funkcja licząca wzrost kapitału przy codziennym procentowym przyroście
function calculateGrowth(initialCapital, dailyPercentage, days) {
  let capital = initialCapital;
  
  for (let day = 1; day <= days; day++) {
    // Przyrost kapitału o ustalony procent dziennie
    const dailyProfit = capital * (dailyPercentage / 100);
    capital += dailyProfit;
    
    console.log(`Dzień ${day}: Kapitał = ${capital.toFixed(2)} zł`);
  }
  
  // Zwróć końcowy kapitał i całkowity zysk
  const totalProfit = capital - initialCapital;
  const percentageIncrease = (totalProfit / initialCapital) * 100;
  
  return {
    finalCapital: capital.toFixed(2),
    totalProfit: totalProfit.toFixed(2),
    percentageIncrease: percentageIncrease.toFixed(2)
  };
}

// Funkcja licząca wzrost kapitału przy miesięcznym przyroście
function calculateMonthlyGrowth(initialCapital, monthlyPercentage, months) {
  let capital = initialCapital;
  let monthlyData = [];
  
  for (let month = 1; month <= months; month++) {
    // Przyrost kapitału o ustalony procent miesięcznie
    const monthlyProfit = capital * (monthlyPercentage / 100);
    capital += monthlyProfit;
    
    monthlyData.push({
      month: month,
      capital: capital.toFixed(2),
      profit: monthlyProfit.toFixed(2)
    });
    
    console.log(`Miesiąc ${month}: Kapitał = ${capital.toFixed(2)} zł (zysk: ${monthlyProfit.toFixed(2)} zł)`);
  }
  
  // Zwróć końcowy kapitał i całkowity zysk
  const totalProfit = capital - initialCapital;
  const percentageIncrease = (totalProfit / initialCapital) * 100;
  
  return {
    finalCapital: capital.toFixed(2),
    totalProfit: totalProfit.toFixed(2),
    percentageIncrease: percentageIncrease.toFixed(2),
    monthlyData: monthlyData
  };
}

// Dane początkowe
const initialCapital = 1000;
const tradingDays = 23;

// Przypadek 1: 5% dziennie
console.log("Scenariusz 1: 5% zysku dziennie");
const result5percent = calculateGrowth(initialCapital, 5, tradingDays);
console.log(`Po ${tradingDays} dniach, przy 5% dziennie:`);
console.log(`- Końcowy kapitał: ${result5percent.finalCapital} zł`);
console.log(`- Całkowity zysk: ${result5percent.totalProfit} zł (${result5percent.percentageIncrease}%)`);
console.log("\n");

// Przypadek 2: 8% dziennie
console.log("Scenariusz 2: 8% zysku dziennie");
const result8percent = calculateGrowth(initialCapital, 8, tradingDays);
console.log(`Po ${tradingDays} dniach, przy 8% dziennie:`);
console.log(`- Końcowy kapitał: ${result8percent.finalCapital} zł`);
console.log(`- Całkowity zysk: ${result8percent.totalProfit} zł (${result8percent.percentageIncrease}%)`);
console.log("\n");

// Przypadek 3: 10% dziennie
console.log("Scenariusz 3: 10% zysku dziennie");
const result10percent = calculateGrowth(initialCapital, 10, tradingDays);
console.log(`Po ${tradingDays} dniach, przy 10% dziennie:`);
console.log(`- Końcowy kapitał: ${result10percent.finalCapital} zł`);
console.log(`- Całkowity zysk: ${result10percent.totalProfit} zł (${result10percent.percentageIncrease}%)`);
console.log("\n");

// Porównanie miesięcznego wzrostu
console.log("Scenariusze miesięcznego wzrostu kapitału");

// Początkowy kapitał dla przykładów miesięcznych
const monthlyInitialCapital = 10000;
const investmentMonths = 12; // rok inwestycji

// Przypadek 1: 15% miesięcznie
console.log("\nScenariusz 1: 15% zysku miesięcznie");
const monthly15percent = calculateMonthlyGrowth(monthlyInitialCapital, 15, investmentMonths);
console.log(`Po ${investmentMonths} miesiącach, przy 15% miesięcznie:`);
console.log(`- Początkowy kapitał: ${monthlyInitialCapital.toFixed(2)} zł`);
console.log(`- Końcowy kapitał: ${monthly15percent.finalCapital} zł`);
console.log(`- Całkowity zysk: ${monthly15percent.totalProfit} zł (${monthly15percent.percentageIncrease}%)`);

// Przypadek 2: 25% miesięcznie
console.log("\nScenariusz 2: 25% zysku miesięcznie");
const monthly25percent = calculateMonthlyGrowth(monthlyInitialCapital, 25, investmentMonths);
console.log(`Po ${investmentMonths} miesiącach, przy 25% miesięcznie:`);
console.log(`- Początkowy kapitał: ${monthlyInitialCapital.toFixed(2)} zł`);
console.log(`- Końcowy kapitał: ${monthly25percent.finalCapital} zł`);
console.log(`- Całkowity zysk: ${monthly25percent.totalProfit} zł (${monthly25percent.percentageIncrease}%)`);

// Przypadek 3: 30% miesięcznie
console.log("\nScenariusz 3: 30% zysku miesięcznie");
const monthly30percent = calculateMonthlyGrowth(monthlyInitialCapital, 30, investmentMonths);
console.log(`Po ${investmentMonths} miesiącach, przy 30% miesięcznie:`);
console.log(`- Początkowy kapitał: ${monthlyInitialCapital.toFixed(2)} zł`);
console.log(`- Końcowy kapitał: ${monthly30percent.finalCapital} zł`);
console.log(`- Całkowity zysk: ${monthly30percent.totalProfit} zł (${monthly30percent.percentageIncrease}%)`); 