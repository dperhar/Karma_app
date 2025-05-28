import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset?: () => void
}) {
  const router = useRouter();

  useEffect(() => {
    // Log the error to an error reporting service
    console.error('Application error:', error);

    // Проверяем, содержит ли сообщение об ошибке упоминание о 401 статусе
    if (error.message.includes('401') || error.message.includes('Unauthorized')) {
      console.log('401 error detected, redirecting to registration page');
      // router.push('/registration-required');
    }
  }, [error, router]);

  // Функция для повторной попытки или возврата на главную
  const handleGoHome = () => {
    router.push('/');
  };

  return (
    <div className="container mx-auto p-4">
      <div className="card bg-base-100 shadow-xl">
        <div className="card-body">
          <div className="flex flex-col gap-2">
            <div className="flex gap-2 text-sm text-body">
              <span className="badge badge-error">Ошибка</span>
            </div>
          </div>
          
          <h2 className="card-title font-kievit text-h3 text-headline">
            Произошла ошибка
          </h2>
          
          <p className="text-body">
            Что-то пошло не так при обработке вашего запроса
          </p>
          
          <div className="bg-base-200 p-3 rounded-lg my-3">
            <code className="text-sm break-words text-body">
              {error.message}
            </code>
          </div>
          
          <div className="divider text-body">Действия</div>
          
          <div className="flex flex-col gap-3">
            {reset && (
              <button 
                className="btn btn-primary btn-lg font-kievit w-full"
                onClick={() => reset()}
              >
                Повторить попытку
              </button>
            )}
            
            <button 
              className="btn btn-outline btn-sm font-kievit"
              onClick={handleGoHome}
            >
              Вернуться на главную
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}