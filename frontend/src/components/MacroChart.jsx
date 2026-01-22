import { useEffect, useRef } from 'react';

export function MacroChart({ macros, totalCalories }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current || !macros) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const radius = 80;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Colors for macros
    const colors = {
      protein: '#FF6B6B',    // Red
      carbs: '#4ECDC4',      // Teal
      fat: '#FFE66D'         // Yellow
    };

    const percentages = macros.macro_percentages || {};
    const protein = percentages.protein || 0;
    const carbs = percentages.carbs || 0;
    const fat = percentages.fat || 0;

    // Draw pie chart
    let currentAngle = -Math.PI / 2;

    // Protein slice
    if (protein > 0) {
      const sliceAngle = (protein / 100) * 2 * Math.PI;
      ctx.fillStyle = colors.protein;
      ctx.beginPath();
      ctx.moveTo(centerX, centerY);
      ctx.arc(centerX, centerY, radius, currentAngle, currentAngle + sliceAngle);
      ctx.closePath();
      ctx.fill();
      currentAngle += sliceAngle;
    }

    // Carbs slice
    if (carbs > 0) {
      const sliceAngle = (carbs / 100) * 2 * Math.PI;
      ctx.fillStyle = colors.carbs;
      ctx.beginPath();
      ctx.moveTo(centerX, centerY);
      ctx.arc(centerX, centerY, radius, currentAngle, currentAngle + sliceAngle);
      ctx.closePath();
      ctx.fill();
      currentAngle += sliceAngle;
    }

    // Fat slice
    if (fat > 0) {
      const sliceAngle = (fat / 100) * 2 * Math.PI;
      ctx.fillStyle = colors.fat;
      ctx.beginPath();
      ctx.moveTo(centerX, centerY);
      ctx.arc(centerX, centerY, radius, currentAngle, currentAngle + sliceAngle);
      ctx.closePath();
      ctx.fill();
    }

    // Draw center circle for donut effect
    ctx.fillStyle = '#1a1a1a';
    ctx.beginPath();
    ctx.arc(centerX, centerY, 50, 0, 2 * Math.PI);
    ctx.fill();

    // Draw center text
    ctx.fillStyle = '#fff';
    ctx.font = 'bold 20px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(Math.round(totalCalories), centerX, centerY - 10);
    ctx.font = '12px sans-serif';
    ctx.fillText('kcal', centerX, centerY + 10);
  }, [macros, totalCalories]);

  if (!macros) {
    return <div className="macro-chart-empty">No data yet</div>;
  }

  const percentages = macros.macro_percentages || {};

  return (
    <div className="macro-chart-container">
      <canvas
        ref={canvasRef}
        width={280}
        height={280}
        className="macro-chart-canvas"
      />
      <div className="macro-legend">
        <div className="legend-item">
          <span className="legend-color" style={{ backgroundColor: '#FF6B6B' }}></span>
          <span className="legend-label">Protein</span>
          <span className="legend-value">{percentages.protein || 0}%</span>
        </div>
        <div className="legend-item">
          <span className="legend-color" style={{ backgroundColor: '#4ECDC4' }}></span>
          <span className="legend-label">Carbs</span>
          <span className="legend-value">{percentages.carbs || 0}%</span>
        </div>
        <div className="legend-item">
          <span className="legend-color" style={{ backgroundColor: '#FFE66D' }}></span>
          <span className="legend-label">Fat</span>
          <span className="legend-value">{percentages.fat || 0}%</span>
        </div>
      </div>
    </div>
  );
}
